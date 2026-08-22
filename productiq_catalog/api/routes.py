"""
ProductIQ Catalog FastAPI Routes — Parallel Catalog Pipeline
=============================================================
Endpoints mounted at /api/catalog/* exposing lookup datasets,
ground truth records, live enrichment, and dual evaluation mechanisms.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from productiq_catalog.lookups.loader import (
    DecimalFractionLookup,
    UOMLookup,
    ManufacturerBrandLookup,
)
from productiq_catalog.ground_truth.ingest import GroundTruthStore
from productiq_catalog.extraction.input_loader import InputDatasetLoader
from productiq_catalog.enrichment.catalog_enricher import CatalogPipeline
from productiq_catalog.scoring.exact_match_eval import ExactMatchEvaluator, ExactMatchEvaluationSummary
from productiq_catalog.scoring.compliance_metrics import ComplianceEvaluator, ComplianceEvaluationSummary

router = APIRouter(prefix="/api/catalog", tags=["Catalog Intelligence (Unilog)"])

# Singletons for fast query responses
_frac_lookup = DecimalFractionLookup()
_uom_lookup = UOMLookup()
_manuf_lookup = ManufacturerBrandLookup()
_ground_truth_store = GroundTruthStore()
_input_loader = InputDatasetLoader()
_pipeline = CatalogPipeline(
    ground_truth=_ground_truth_store,
)
_exact_evaluator = ExactMatchEvaluator(
    pipeline=_pipeline,
    ground_truth=_ground_truth_store,
    input_loader=_input_loader,
)
_compliance_evaluator = ComplianceEvaluator(
    pipeline=_pipeline,
    input_loader=_input_loader,
)


class CatalogHealthDTO(BaseModel):
    status: str
    service: str
    input_rows_loaded: int
    ground_truth_rows_loaded: int
    decimal_fractions_loaded: int
    manufacturer_mappings_loaded: int


@router.get("/health", response_model=CatalogHealthDTO)
def catalog_health():
    """
    Sanity-check health endpoint verifying all catalog datasets are loaded.
    """
    return CatalogHealthDTO(
        status="ok",
        service="ProductIQ Unilog Catalog Pipeline",
        input_rows_loaded=_input_loader.count(),
        ground_truth_rows_loaded=_ground_truth_store.count(),
        decimal_fractions_loaded=len(_frac_lookup.get_all_entries()),
        manufacturer_mappings_loaded=len(_manuf_lookup.get_all_mappings()),
    )


@router.get("/lookups/manufacturers")
def get_manufacturers(query: Optional[str] = Query(None, description="Search query signal")):
    """
    Retrieve master manufacturer and brand mappings or query by signal.
    """
    if query:
        matched = _manuf_lookup.match_signal(query)
        if not matched:
            return {"query": query, "matched": False, "result": None}
        return {"query": query, "matched": True, "result": matched}

    return {
        "total_mappings": len(_manuf_lookup.get_all_mappings()),
        "mappings": _manuf_lookup.get_all_mappings(),
    }


@router.get("/lookups/uom")
def get_uom_standards(alias: Optional[str] = Query(None, description="Raw unit alias to normalize")):
    """
    Retrieve UOM standards or test normalizing a specific alias.
    """
    if alias:
        canon = _uom_lookup.normalize(alias)
        return {"raw_alias": alias, "canonical_uom": canon}

    return {
        "description": "ProductIQ UOM Standards Table (Strict Ground Truth Verified)",
        "canonical_units": _uom_lookup.get_canonical_units(),
    }


@router.get("/lookups/fractions")
def get_decimal_fractions(fraction: Optional[str] = Query(None, description="Fraction string e.g. 7/64 or 1-1/2")):
    """
    Retrieve the 63 standard decimal-fraction table entries or convert a fraction.
    """
    if fraction:
        dec = _frac_lookup.parse_fraction(fraction)
        return {"fraction": fraction, "decimal": dec}

    return {
        "total_entries": len(_frac_lookup.get_all_entries()),
        "entries": _frac_lookup.get_all_entries(),
    }


@router.get("/input/{row_id}")
def get_input_row(row_id: int):
    """
    Retrieve a raw input row from the 1,000-item dataset.
    """
    row = _input_loader.get_by_row_id(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Input row {row_id} not found (valid range: 1..1000)")
    return row.to_dict()


@router.get("/ground-truth/{row_id}")
def get_ground_truth(row_id: int):
    """
    Retrieve ground truth expected output record for benchmarking.
    """
    rec = _ground_truth_store.get_by_row_id(row_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Ground truth record {row_id} not found (valid range: 1..{_ground_truth_store.count()})")
    return rec.to_dict()


@router.post("/enrich/{row_id}")
def enrich_input_row(row_id: int):
    """
    Execute full catalog enrichment pipeline for a single input row.
    Returns scoped fields, 4-tier trust statuses, normalized attributes, and conflict flags.
    """
    row = _input_loader.get_by_row_id(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Input row {row_id} not found (valid range: 1..1000)")
    product = _pipeline.process_row(row)
    return product.to_dict()


@router.get("/eval/exact-match", response_model=ExactMatchEvaluationSummary)
def evaluate_exact_match():
    """
    Mechanism A: Exact-match evaluation against the 2 verified gold-standard rows.
    Explicitly reports n=2 and field-by-field comparisons.
    """
    return _exact_evaluator.evaluate()


@router.get("/eval/compliance", response_model=ComplianceEvaluationSummary)
def evaluate_compliance(force_refresh: bool = Query(False, description="Force recomputation of 1000-row batch")):
    """
    Mechanism B: Rule-compliance and vocabulary metrics across all 1,000 input rows.
    Reports LOV compliance, conflict detection rate, placeholder filtering, status distribution, and latency.
    """
    return _compliance_evaluator.evaluate(force_refresh=force_refresh)
