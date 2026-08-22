"""
ProductIQ Catalog Enrichment & Dual Evaluation Test Suite — Prompt 2
====================================================================
Tests manufacturer canonicalization, conflict detection across 1,000 items,
UOM & decimal-fraction normalization, Mechanism A exact-match evaluation (n=2),
Mechanism B rule compliance at scale (1,000 items), and live FastAPI routes.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from productiq_catalog.schema.models import (
    CatalogTrustStatus,
    CatalogField,
    CatalogAttributeTriple,
    CatalogInputRow,
    CatalogProduct,
)
from productiq_catalog.enrichment.manufacturer_enricher import ManufacturerEnricher
from productiq_catalog.enrichment.uom_enricher import UOMEnricher
from productiq_catalog.enrichment.catalog_enricher import CatalogPipeline
from productiq_catalog.scoring.exact_match_eval import ExactMatchEvaluator
from productiq_catalog.scoring.compliance_metrics import ComplianceEvaluator
from productiq.api.app import app

client = TestClient(app)


class TestManufacturerEnrichment:
    """Test manufacturer canonicalization, conflict detection, and no-fabrication discipline."""

    def test_exact_match_verified(self):
        enricher = ManufacturerEnricher()
        row = CatalogInputRow(
            row_id=1,
            mfg_part_num="PDSH4816AF",
            part_desc="PDSH4816AF Dishwasher SS - Display Only",
            part_manuf="Appliance Dealers Cooperative (APPDE)",
        )
        res = enricher.enrich(row)
        assert res["manufacturer_name"].value == "Rheem Manufacturing"
        assert res["manufacturer_name"].status == CatalogTrustStatus.VERIFIED
        assert res["manufacturer_name"].confidence == 1.0
        assert "FRIGIDAIRE" in (res["brand_name"].value or "")
        assert res["brand_name"].status == CatalogTrustStatus.VERIFIED

    def test_unverified_supplier_resolves_to_unknown(self):
        enricher = ManufacturerEnricher()
        row = CatalogInputRow(
            row_id=10,
            mfg_part_num="XYZ-12345",
            part_desc="Random Industrial Tool",
            part_manuf="Unverified Generic Supplier (9999)",
        )
        res = enricher.enrich(row)
        assert res["manufacturer_name"].value is None
        assert res["manufacturer_name"].status == CatalogTrustStatus.UNKNOWN
        assert res["manufacturer_name"].confidence == 0.0
        assert res["brand_name"].value is None
        assert res["brand_name"].status == CatalogTrustStatus.UNKNOWN

    def test_conflict_detection_across_disagreeing_brands(self):
        enricher = ManufacturerEnricher()
        row = CatalogInputRow(
            row_id=20,
            mfg_part_num="TEST-CONFLICT-01",
            part_desc="Conflicted Brand Item",
            e1_brand="TREX",
            dib_brand="Milwaukee",
            part_manuf="Freud Inc (2435)",
        )
        res = enricher.enrich(row)
        assert res["brand_name"].status == CatalogTrustStatus.CONFLICTED
        assert res["brand_name"].value is None  # No arbitrary winner picked
        assert res["brand_name"].confidence == 0.40
        assert "Conflict" in res["brand_name"].reason


class TestUOMAndFractionEnrichment:
    """Test unit normalization and decimal fraction conversions."""

    def test_canonical_unit_normalization(self):
        enricher = UOMEnricher()
        canon, status = enricher.normalize_unit("V")
        assert canon == "V"
        assert status == CatalogTrustStatus.VERIFIED

        canon_alias, status_alias = enricher.normalize_unit("IN")
        assert canon_alias == "in"
        assert status_alias == CatalogTrustStatus.INFERRED

        canon_quote, status_quote = enricher.normalize_unit('"')
        assert canon_quote == "in"
        assert status_quote == CatalogTrustStatus.INFERRED

    def test_fraction_and_dimension_conversion(self):
        enricher = UOMEnricher()
        triple = enricher.normalize_value_and_unit(raw_val_str="50-1/4", raw_unit_str="IN", label="Depth")
        assert triple.value == 50.25
        assert triple.uom == "in"
        assert triple.status == CatalogTrustStatus.INFERRED

        triple_frac = enricher.normalize_value_and_unit(raw_val_str="7/8", raw_unit_str='"', label="Size")
        assert triple_frac.value == 0.875
        assert triple_frac.uom == "in"

    def test_text_attribute_extraction(self):
        enricher = UOMEnricher()
        text = "DISHWASHER LEG 5 SST 120V 15A 41DBA 50-1/4IN"
        attrs = enricher.extract_attributes_from_text(text)
        assert len(attrs) >= 3
        labels = [a.label for a in attrs]
        assert "Voltage Rating" in labels
        assert "Amperage Rating" in labels
        assert "Sound Level" in labels


class TestCatalogPipelineEndToEnd:
    """Test full pipeline row processing."""

    def test_pipeline_row_processing(self):
        pipeline = CatalogPipeline()
        row = CatalogInputRow(
            row_id=1,
            mfg_part_num="PDSH4816AF",
            part_desc="PDSH4816AF Dishwasher SS - Display Only",
            part_manuf="Appliance Dealers Cooperative (APPDE)",
        )
        product = pipeline.process_row(row)
        assert product.mfg_part_num == "PDSH4816AF"
        assert product.manufacturer_name.value == "Rheem Manufacturing"
        assert "FRIGIDAIRE" in (product.brand_name.value or "")
        assert product.overall_trust_status == CatalogTrustStatus.VERIFIED


class TestDualEvaluationMechanisms:
    """Test Mechanism A (Exact-Match n=2) and Mechanism B (Compliance at Scale 1000 items)."""

    def test_mechanism_a_exact_match(self):
        evaluator = ExactMatchEvaluator()
        summary = evaluator.evaluate()
        assert summary.sample_size_n == 2
        assert "n=2" in summary.sample_size_label
        assert "n=2" in summary.summary_statement
        assert summary.total_fields_compared >= 10
        assert summary.overall_exact_match_rate_pct == 100.0
        assert len(summary.rows) == 2

    def test_mechanism_b_compliance_scale(self):
        evaluator = ComplianceEvaluator()
        summary = evaluator.evaluate()
        assert summary.total_input_rows == 1000
        assert summary.lov_compliance_rate_pct == 100.0
        assert summary.placeholder_filtering_rate_pct > 0.0
        assert summary.total_duration_ms > 0.0
        assert summary.throughput_rows_per_second > 0.0
        # Status distribution sums to 100%
        m_dist = summary.manufacturer_status_distribution
        assert round(m_dist.verified_pct + m_dist.inferred_pct + m_dist.conflicted_pct + m_dist.unknown_pct, 1) == 100.0


class TestCatalogEnrichmentAPIRoutes:
    """Test live FastAPI endpoints for enrichment and evaluation."""

    def test_enrich_endpoint(self):
        resp = client.post("/api/catalog/enrich/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_id"] == 1
        assert "manufacturer_name" in data
        assert "brand_name" in data
        assert "overall_trust_status" in data

    def test_exact_match_eval_endpoint(self):
        resp = client.get("/api/catalog/eval/exact-match")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_size_n"] == 2
        assert "n=2" in data["sample_size_label"]
        assert data["overall_exact_match_rate_pct"] == 100.0

    def test_compliance_eval_endpoint(self):
        resp = client.get("/api/catalog/eval/compliance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_input_rows"] == 1000
        assert data["lov_compliance_rate_pct"] == 100.0
        assert "throughput_rows_per_second" in data
