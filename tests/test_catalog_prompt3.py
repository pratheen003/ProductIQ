"""
ProductIQ Catalog Prompt 3 Test Suite
======================================
Tests Mechanism A relabeling/disclaimer framing, full 1,000-row batch persistence,
catalog explorer & product detail API endpoints, and deck numbers exporter.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from productiq_catalog.scoring.exact_match_eval import ExactMatchEvaluator
from productiq_catalog.scoring.compliance_metrics import ComplianceEvaluator
from scripts.export_deck_numbers import export_deck_numbers
from productiq.api.app import app

client = TestClient(app)


class TestMechanismAReframing:
    """Test corrected framing and disclaimers for Mechanism A."""

    def test_exact_match_fidelity_relabeling(self):
        evaluator = ExactMatchEvaluator()
        summary = evaluator.evaluate()
        assert "Pipeline Correctness & Formatting Fidelity" in summary.metric_label
        assert "n=2" in summary.metric_label
        assert summary.sample_size_n == 2
        assert "This validates that the enrichment pipeline correctly reproduces" in summary.disclaimer
        assert "unseen manufacturers" in summary.disclaimer

    def test_api_exact_match_endpoint_relabeling(self):
        resp = client.get("/api/catalog/eval/exact-match")
        assert resp.status_code == 200
        data = resp.json()
        assert "Pipeline Correctness & Formatting Fidelity" in data["metric_label"]
        assert "disclaimer" in data
        assert len(data["disclaimer"]) > 50


class TestBatchPersistence:
    """Test full 1,000-row batch persistence to data/catalog/processed/."""

    def test_persisted_files_exist_and_complete(self):
        processed_dir = Path(__file__).resolve().parent.parent / "data" / "catalog" / "processed"
        assert processed_dir.exists(), "Processed directory must exist"

        batch_file = processed_dir / "batch_catalog_report.json"
        assert batch_file.exists(), "batch_catalog_report.json must exist"

        with open(batch_file, "r", encoding="utf-8") as f:
            batch_data = json.load(f)

        assert batch_data["total_records"] == 1000
        assert batch_data["persisted_files_count"] == 1000
        assert batch_data["conflict_count"] == 392

        # Check individual row files
        row_1 = processed_dir / "row_0001.json"
        row_1000 = processed_dir / "row_1000.json"
        assert row_1.exists()
        assert row_1000.exists()


class TestCatalogAPIEndpointsPrompt3:
    """Test new catalog explorer, product detail, and batch summary routes."""

    def test_get_catalog_products_paginated(self):
        resp = client.get("/api/catalog/products?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1000
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["items"]) == 10

    def test_get_catalog_products_filter_status(self):
        resp = client.get("/api/catalog/products?status=Verified")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["overall_status"] == "Verified"

    def test_get_catalog_products_filter_conflicts(self):
        resp = client.get("/api/catalog/products?has_conflicts=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 392

    def test_get_catalog_product_detail(self):
        resp = client.get("/api/catalog/products/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_id"] == 1
        assert "manufacturer_name" in data
        assert "brand_name" in data
        assert "attributes" in data

    def test_get_batch_summary(self):
        resp = client.get("/api/catalog/batch/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_records"] == 1000
        assert data["conflict_count"] == 392


class TestDeckNumbersExport:
    """Test export_deck_numbers script."""

    def test_deck_numbers_exported_successfully(self):
        output = export_deck_numbers()
        assert "ProductIQ — Deck-Ready Numbers" in output
        assert "Pipeline Correctness & Formatting Fidelity" in output
        assert "100.0%" in output
        assert "39.2%" in output

        deck_file = Path(__file__).resolve().parent.parent / "docs" / "DECK_NUMBERS.md"
        assert deck_file.exists()
        content = deck_file.read_text(encoding="utf-8")
        assert len(content) > 1000
