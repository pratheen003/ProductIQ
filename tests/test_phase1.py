"""
test_phase1.py
==============
Integration tests for Phase 1 — verifying that:
  - All extraction modules are importable
  - The batch extraction command works
  - Processed output exists and is valid JSON
  - All 12 products produce output
  - Phase 0 baseline is not broken
"""
import json
import pytest
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
MANIFEST_PATH = Path(__file__).parent.parent / "data" / "dataset_manifest.json"
SUMMARY_PATH = PROCESSED_DIR / "extraction_summary.json"

EXPECTED_PRODUCTS = [
    "PIQ-W22SP-4P-1.1", "PIQ-W22SP-4P-1.5", "PIQ-W22SP-4P-2.2",
    "PIQ-W22SP-4P-3.0", "PIQ-W22SP-4P-4.0", "PIQ-W22SP-4P-5.5",
    "PIQ-W22SP-4P-7.5", "PIQ-W22SP-4P-9.2", "PIQ-W22SP-4P-11",
    "PIQ-W22SP-4P-15", "PIQ-W22SP-6P-0.75", "PIQ-W22SP-6P-1.1",
]


class TestPhase1Imports:
    def test_extraction_package_importable(self):
        import productiq.extraction
        assert productiq.extraction is not None

    def test_evidence_record_importable(self):
        from productiq.extraction import EvidenceRecord
        assert EvidenceRecord is not None

    def test_extraction_result_importable(self):
        from productiq.extraction import ExtractionResult
        assert ExtractionResult is not None

    def test_pdf_extractor_importable(self):
        from productiq.extraction import PDFExtractor
        assert PDFExtractor is not None

    def test_csv_extractor_importable(self):
        from productiq.extraction import CSVExtractor
        assert CSVExtractor is not None

    def test_web_extractor_importable(self):
        from productiq.extraction import WebExtractor
        assert WebExtractor is not None

    def test_batch_summary_importable(self):
        from productiq.extraction import BatchExtractionSummary
        assert BatchExtractionSummary is not None

    def test_models_module_importable(self):
        from productiq.extraction import models
        assert models is not None


class TestPhase0StillValid:
    """Regression: Phase 0 schema must not have been broken by Phase 1."""

    def test_schema_still_importable(self):
        from productiq.schema import MotorProduct, DataStatus, FieldValue, SourceEntry
        assert MotorProduct is not None

    def test_data_status_still_has_four_values(self):
        from productiq.schema import DataStatus
        assert len(DataStatus) == 4

    def test_motor_product_still_instantiates(self):
        from productiq.schema import MotorProduct
        m = MotorProduct(product_id="PIQ-TEST", manufacturer="TestCo", model="TestModel")
        assert m.product_id == "PIQ-TEST"

    def test_schema_version_unchanged(self):
        from productiq.schema import MotorProduct
        m = MotorProduct(product_id="x", manufacturer="y", model="z")
        assert m.schema_version == "0.1.0-phase0"

    def test_field_value_constraints_still_enforced(self):
        from productiq.schema import FieldValue, DataStatus
        import pydantic
        with pytest.raises((ValueError, pydantic.ValidationError)):
            FieldValue(value=5.0, status=DataStatus.UNKNOWN)

    def test_source_entry_still_works(self):
        from productiq.schema import SourceEntry, SourceType
        s = SourceEntry(
            source_id="test",
            source_type=SourceType.PDF,
            location="p.5",
            reference="test.pdf",
        )
        assert s.source_type == SourceType.PDF


class TestProcessedOutputExists:
    """Verify that the batch extraction produced output on disk."""

    def test_processed_dir_exists(self):
        assert PROCESSED_DIR.exists(), f"Processed dir missing: {PROCESSED_DIR}"

    def test_summary_file_exists(self):
        assert SUMMARY_PATH.exists(), (
            "extraction_summary.json not found. Run: python scripts/run_extraction.py"
        )

    def test_summary_is_valid_json(self):
        if not SUMMARY_PATH.exists():
            pytest.skip("summary not generated yet")
        data = json.loads(SUMMARY_PATH.read_text())
        assert isinstance(data, dict)

    def test_summary_has_expected_fields(self):
        if not SUMMARY_PATH.exists():
            pytest.skip("summary not generated yet")
        data = json.loads(SUMMARY_PATH.read_text())
        assert "products_discovered" in data
        assert "csv_succeeded" in data
        assert "pdf_succeeded" in data

    def test_12_products_in_summary(self):
        if not SUMMARY_PATH.exists():
            pytest.skip("summary not generated yet")
        data = json.loads(SUMMARY_PATH.read_text())
        assert data.get("products_discovered") == 12

    def test_product_output_dirs_exist(self):
        missing = []
        for pid in EXPECTED_PRODUCTS:
            pid_dir = PROCESSED_DIR / pid
            if not pid_dir.exists():
                missing.append(pid)
        assert not missing, f"Missing output dirs for: {missing}"


class TestPerProductOutput:
    """Verify that each product has valid JSON evidence files."""

    @pytest.mark.parametrize("product_id", EXPECTED_PRODUCTS)
    def test_csv_evidence_exists_and_valid(self, product_id):
        csv_file = PROCESSED_DIR / product_id / "csv_evidence.json"
        assert csv_file.exists(), f"Missing csv_evidence.json for {product_id}"
        data = json.loads(csv_file.read_text())
        assert data["product_id"] == product_id
        assert data["source_type"] == "csv"

    @pytest.mark.parametrize("product_id", EXPECTED_PRODUCTS)
    def test_pdf_evidence_exists_and_valid(self, product_id):
        pdf_file = PROCESSED_DIR / product_id / "pdf_evidence.json"
        assert pdf_file.exists(), f"Missing pdf_evidence.json for {product_id}"
        data = json.loads(pdf_file.read_text())
        assert data["product_id"] == product_id
        assert data["source_type"] == "pdf"

    @pytest.mark.parametrize("product_id", EXPECTED_PRODUCTS)
    def test_web_evidence_exists_and_valid(self, product_id):
        """Web evidence must exist (even if failed — failure is correctly documented)."""
        web_file = PROCESSED_DIR / product_id / "web_evidence.json"
        assert web_file.exists(), f"Missing web_evidence.json for {product_id}"
        data = json.loads(web_file.read_text())
        assert data["product_id"] == product_id
        assert data["source_type"] == "web"
        # Status is either success (if web worked) or failed (if 403) — both valid
        assert data["status"] in ("success", "failed", "partial")

    @pytest.mark.parametrize("product_id", EXPECTED_PRODUCTS)
    def test_pdf_evidence_has_evidence_records(self, product_id):
        pdf_file = PROCESSED_DIR / product_id / "pdf_evidence.json"
        if not pdf_file.exists():
            pytest.skip(f"pdf_evidence.json not found for {product_id}")
        data = json.loads(pdf_file.read_text())
        assert len(data["evidence"]) > 0, f"{product_id}: PDF evidence list is empty"

    @pytest.mark.parametrize("product_id", EXPECTED_PRODUCTS)
    def test_csv_evidence_has_evidence_records(self, product_id):
        csv_file = PROCESSED_DIR / product_id / "csv_evidence.json"
        if not csv_file.exists():
            pytest.skip(f"csv_evidence.json not found for {product_id}")
        data = json.loads(csv_file.read_text())
        assert len(data["evidence"]) > 0, f"{product_id}: CSV evidence list is empty"


class TestEvidenceIntegrity:
    """Verify the quality bar — real values, no fabrication, provenance intact."""

    def test_pdf_rated_power_matches_product_id(self):
        """The rated_power in PDF evidence must match what the product_id implies."""
        pdf_file = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "pdf_evidence.json"
        if not pdf_file.exists():
            pytest.skip("PDF evidence not generated")
        data = json.loads(pdf_file.read_text())
        power_records = [e for e in data["evidence"] if e["attribute"] == "rated_power"]
        assert power_records, "No rated_power records in PDF evidence"
        values = [e["value"] for e in power_records if e["value"] is not None]
        assert any(abs(v - 1.1) < 0.05 for v in values), (
            f"Expected 1.1 kW, got {values}"
        )

    def test_csv_weight_value_correct(self):
        """The weight from CSV must be the real value from the WEG brochure."""
        csv_file = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "csv_evidence.json"
        if not csv_file.exists():
            pytest.skip("CSV evidence not generated")
        data = json.loads(csv_file.read_text())
        weight_records = [e for e in data["evidence"] if e["attribute"] == "weight"]
        assert weight_records, "No weight records in CSV evidence"
        values = [e["value"] for e in weight_records if e["value"] is not None]
        assert any(abs(v - 19.5) < 0.5 for v in values), (
            f"Expected 19.5 kg, got {values}"
        )

    def test_web_failure_has_error_not_evidence(self):
        """When web fetch fails, there must be an error message, not fabricated evidence."""
        web_file = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "web_evidence.json"
        if not web_file.exists():
            pytest.skip("Web evidence not generated")
        data = json.loads(web_file.read_text())
        if data["status"] == "failed":
            assert data["error"] is not None, "Failed extraction must have an error"
            assert len(data["evidence"]) == 0, "Failed extraction must have no evidence"
