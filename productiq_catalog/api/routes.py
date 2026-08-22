"""
ProductIQ Catalog FastAPI Routes — Parallel Catalog Pipeline
=============================================================
Endpoints mounted at /api/catalog/* exposing lookup datasets,
ground truth records, live enrichment, batch results, and dual evaluation mechanisms.
"""
from __future__ import annotations

import json
from pathlib import Path
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

_processed_dir = Path(__file__).resolve().parent.parent.parent / "data" / "catalog" / "processed"


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


@router.get("/products")
def get_catalog_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by trust status (Verified, Inferred, Conflicted, Unknown)"),
    search: Optional[str] = Query(None, description="Search by part number or description"),
    has_conflicts: Optional[bool] = Query(None, description="Filter items with detected conflicts"),
):
    """
    Retrieve paginated list of catalog products across the 1,000-item dataset.
    """
    # Prefer pre-persisted batch report if available, else compute on the fly
    batch_file = _processed_dir / "batch_catalog_report.json"
    if batch_file.exists():
        with open(batch_file, "r", encoding="utf-8") as f:
            batch_data = json.load(f)
        records = batch_data.get("records_summary", [])
    else:
        # Fallback to computing summaries on the fly
        all_rows = _input_loader.get_all()
        records = []
        for r in all_rows:
            p = _pipeline.process_row(r)
            records.append({
                "row_id": p.row_id,
                "mfg_part_num": p.mfg_part_num,
                "part_desc": p.part_desc,
                "manufacturer": p.manufacturer_name.value,
                "brand": p.brand_name.value,
                "overall_status": p.overall_trust_status.value,
                "confidence": p.overall_confidence,
                "has_conflicts": p.has_conflicts,
            })

    # Apply filters
    filtered = records
    if status:
        filtered = [r for r in filtered if r["overall_status"].lower() == status.lower()]
    if has_conflicts is not None:
        filtered = [r for r in filtered if r["has_conflicts"] == has_conflicts]
    if search:
        s_lower = search.lower()
        filtered = [
            r for r in filtered
            if s_lower in r["mfg_part_num"].lower()
            or (r["part_desc"] and s_lower in r["part_desc"].lower())
            or (r["brand"] and s_lower in r["brand"].lower())
        ]

    total_filtered = len(filtered)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_records = filtered[start_idx:end_idx]

    return {
        "total": total_filtered,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_filtered + page_size - 1) // page_size if page_size > 0 else 1,
        "items": page_records,
    }


@router.get("/products/{row_id}")
def get_catalog_product_detail(row_id: int):
    """
    Retrieve full product detail with enriched fields, attribute triples, and conflict reasoning.
    """
    row_file = _processed_dir / f"row_{row_id:04d}.json"
    if row_file.exists():
        with open(row_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback to pipeline execution if file not yet on disk
    row = _input_loader.get_by_row_id(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Product with row_id {row_id} not found")
    return _pipeline.process_row(row).to_dict()


@router.get("/batch/summary")
def get_batch_summary():
    """
    Retrieve batch processing statistics and status distributions across the 1,000-item dataset.
    """
    batch_file = _processed_dir / "batch_catalog_report.json"
    if batch_file.exists():
        with open(batch_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # Compute via compliance evaluator if not on disk
    summary = _compliance_evaluator.evaluate()
    return {
        "batch_id": "UNILOG-CATALOG-1000",
        "total_records": summary.total_input_rows,
        "duration_ms": summary.total_duration_ms,
        "throughput_rows_per_second": summary.throughput_rows_per_second,
        "conflict_count": summary.total_conflicts_detected,
        "conflict_rate_pct": summary.conflict_detection_rate_pct,
        "status_distribution": {
            "Verified": summary.overall_status_distribution.verified_count,
            "Inferred": summary.overall_status_distribution.inferred_count,
            "Conflicted": summary.overall_status_distribution.conflicted_count,
            "Unknown": summary.overall_status_distribution.unknown_count,
        },
        "status_distribution_pct": {
            "Verified": summary.overall_status_distribution.verified_pct,
            "Inferred": summary.overall_status_distribution.inferred_pct,
            "Conflicted": summary.overall_status_distribution.conflicted_pct,
            "Unknown": summary.overall_status_distribution.unknown_pct,
        },
    }


@router.get("/eval/exact-match", response_model=ExactMatchEvaluationSummary)
def evaluate_exact_match():
    """
    Mechanism A: Pipeline correctness & formatting fidelity evaluation on the 2 gold-standard rows.
    Explicitly reports n=2, field-by-field comparisons, and disclaimer.
    """
    return _exact_evaluator.evaluate()


@router.get("/eval/compliance", response_model=ComplianceEvaluationSummary)
def evaluate_compliance(force_refresh: bool = Query(False, description="Force recomputation of 1000-row batch")):
    """
    Mechanism B: Rule-compliance and vocabulary metrics across all 1,000 input rows.
    Reports LOV compliance, conflict detection rate, placeholder filtering, status distribution, and latency.
    """
    return _compliance_evaluator.evaluate(force_refresh=force_refresh)


@router.get("/export/delivery-format")
def export_delivery_format(format: str = Query("xlsx", pattern="^(xlsx|csv)$", description="File format (xlsx or csv)")):
    """
    Download the full 1,000-row enriched dataset in the exact 252-column schema of Unihack Expected Output.
    """
    from fastapi.responses import FileResponse

    # Ensure robust absolute path resolution independent of CWD
    app_root = Path(__file__).resolve().parent.parent.parent
    processed_dir = app_root / "data" / "catalog" / "processed"
    filename = f"productiq_delivery_output.{format}"
    file_path = processed_dir / filename

    if not file_path.exists():
        try:
            from productiq_catalog.export.delivery_format_exporter import DeliveryFormatExporter
            exporter = DeliveryFormatExporter(output_dir=processed_dir)
            exporter.export_all(pipeline=_pipeline, input_loader=_input_loader)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate delivery export file ({filename}): {str(e)}",
            )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Delivery export file not found at {file_path}",
        )

    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if format == "xlsx"
        else "text/csv; charset=utf-8"
    )

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


