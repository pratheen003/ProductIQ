"""
test_extraction_pdf.py
=======================
Tests for the PDF extractor against the real WEG brochure.

Integration tests use the real PDF in data/pdf/.
Tests are skipped if the PDF is not found (not a code failure).
"""
import json
import pytest
from pathlib import Path

PDF_PATH = Path(__file__).parent.parent / "data" / "pdf" / "WEG_W22_Severe_Process_IE3_Brochure.pdf"
MANIFEST_PATH = Path(__file__).parent.parent / "data" / "dataset_manifest.json"

pytestmark = []


def _load_manifest():
    if not MANIFEST_PATH.exists():
        return {}
    import json
    with open(MANIFEST_PATH) as f:
        products = json.load(f)
    return {p["product_id"]: p for p in products}


@pytest.fixture(scope="module")
def pdf_extractor():
    from productiq.extraction import PDFExtractor
    if not PDF_PATH.exists():
        pytest.skip(f"PDF not found: {PDF_PATH}")
    manifest = _load_manifest()
    return PDFExtractor(
        pdf_path=PDF_PATH,
        source_id="WEG_W22_Severe_Process_IE3_Brochure",
        manifest_products=manifest,
    )


@pytest.fixture(scope="module")
def pdf_results(pdf_extractor):
    return pdf_extractor.extract_all()


class TestPDFExtractorInit:
    def test_extractor_importable(self):
        from productiq.extraction import PDFExtractor
        assert PDFExtractor is not None

    def test_extractor_instantiates(self):
        from productiq.extraction import PDFExtractor
        extractor = PDFExtractor(
            pdf_path=Path("/nonexistent.pdf"),
            source_id="test",
            manifest_products={},
        )
        assert extractor is not None

    def test_missing_pdf_returns_failure(self):
        from productiq.extraction import PDFExtractor
        extractor = PDFExtractor(
            pdf_path=Path("/nonexistent.pdf"),
            source_id="test",
            manifest_products={},
        )
        results = extractor.extract_all()
        assert len(results) == 1
        assert results[0].succeeded is False
        assert "not found" in results[0].error.lower()


class TestPDFExtractionResults:
    def test_extraction_returns_list(self, pdf_results):
        assert isinstance(pdf_results, list)

    def test_at_least_one_result(self, pdf_results):
        assert len(pdf_results) >= 1

    def test_all_results_have_source_id(self, pdf_results):
        for r in pdf_results:
            assert r.source_id == "WEG_W22_Severe_Process_IE3_Brochure"

    def test_all_results_have_source_type_pdf(self, pdf_results):
        for r in pdf_results:
            assert r.source_type == "pdf"

    def test_known_products_extracted(self, pdf_results):
        pids = {r.product_id for r in pdf_results}
        # All 12 manifest products should be matched
        expected = {
            "PIQ-W22SP-4P-1.1", "PIQ-W22SP-4P-1.5", "PIQ-W22SP-4P-2.2",
            "PIQ-W22SP-4P-3.0", "PIQ-W22SP-4P-4.0", "PIQ-W22SP-4P-5.5",
            "PIQ-W22SP-4P-7.5", "PIQ-W22SP-4P-9.2", "PIQ-W22SP-4P-11",
            "PIQ-W22SP-4P-15", "PIQ-W22SP-6P-0.75", "PIQ-W22SP-6P-1.1",
        }
        matched = pids & expected
        assert len(matched) >= 10, (
            f"Expected at least 10 known products, got {len(matched)}: {matched}"
        )

    def test_all_results_have_success_status(self, pdf_results):
        from productiq.extraction.models import ExtractionStatus
        known_results = [r for r in pdf_results if r.product_id.startswith("PIQ-")]
        for r in known_results:
            assert r.status == ExtractionStatus.SUCCESS.value, (
                f"Product {r.product_id} has status={r.status}, error={r.error}"
            )

    def test_each_result_has_evidence(self, pdf_results):
        known = [r for r in pdf_results if r.product_id.startswith("PIQ-")]
        for r in known:
            assert r.evidence_count > 0, f"{r.product_id} has no evidence"

    def test_pages_read_recorded(self, pdf_results):
        for r in pdf_results:
            assert r.pages_read is not None
            assert r.pages_read > 0


class TestPDFEvidenceProvenance:
    def test_all_evidence_has_page(self, pdf_results):
        for result in pdf_results:
            for e in result.evidence:
                if e.source_type == "pdf" and e.method == "table":
                    assert e.page is not None, f"Evidence for {e.attribute} missing page"

    def test_all_evidence_has_source_id(self, pdf_results):
        for result in pdf_results:
            for e in result.evidence:
                assert e.source_id

    def test_all_evidence_has_attribute(self, pdf_results):
        for result in pdf_results:
            for e in result.evidence:
                assert e.attribute, "EvidenceRecord has empty attribute"

    def test_all_evidence_has_raw_value(self, pdf_results):
        for result in pdf_results:
            for e in result.evidence:
                assert e.raw_value is not None, f"Missing raw_value for {e.attribute}"


class TestPDFRepresentativeValues:
    """Verify that key motor spec values are actually extracted from the real PDF."""

    def _get_records_for(self, pdf_results, product_id, attribute):
        for result in pdf_results:
            if result.product_id == product_id:
                return [e for e in result.evidence if e.attribute == attribute]
        return []

    def test_rated_power_extracted(self, pdf_results):
        records = self._get_records_for(pdf_results, "PIQ-W22SP-4P-1.1", "rated_power")
        assert records, "rated_power not found for 1.1 kW motor"
        assert any(abs(r.value - 1.1) < 0.05 for r in records if r.value), (
            f"Expected 1.1 kW, got {[r.value for r in records]}"
        )

    def test_rated_speed_extracted(self, pdf_results):
        records = self._get_records_for(pdf_results, "PIQ-W22SP-4P-1.1", "rated_speed")
        assert records, "rated_speed not found for 1.1 kW motor"
        assert any(abs(r.value - 1455) < 10 for r in records if r.value), (
            f"Expected ~1455 rpm, got {[r.value for r in records]}"
        )

    def test_efficiency_extracted(self, pdf_results):
        records = self._get_records_for(pdf_results, "PIQ-W22SP-4P-1.1", "efficiency")
        assert records, "efficiency not found for 1.1 kW motor"
        assert any(r.value is not None for r in records), "efficiency value is None"

    def test_power_factor_extracted(self, pdf_results):
        records = self._get_records_for(pdf_results, "PIQ-W22SP-4P-1.1", "power_factor")
        assert records, "power_factor not found for 1.1 kW motor"

    def test_weight_extracted(self, pdf_results):
        records = self._get_records_for(pdf_results, "PIQ-W22SP-4P-1.1", "weight")
        assert records, "weight not found for 1.1 kW motor"
        assert any(abs(r.value - 19.5) < 1.0 for r in records if r.value), (
            f"Expected 19.5 kg, got {[r.value for r in records]}"
        )

    def test_frame_size_extracted(self, pdf_results):
        records = self._get_records_for(pdf_results, "PIQ-W22SP-4P-1.1", "frame_size")
        assert records, "frame_size not found for 1.1 kW motor"
        assert any(r.raw_value for r in records), "frame_size raw_value is empty"

    def test_6pole_product_extracted(self, pdf_results):
        records = self._get_records_for(pdf_results, "PIQ-W22SP-6P-1.1", "rated_power")
        assert records, "6-pole 1.1 kW motor not extracted from PDF"
        assert any(abs(r.value - 1.1) < 0.05 for r in records if r.value)

    def test_units_recorded(self, pdf_results):
        records = self._get_records_for(pdf_results, "PIQ-W22SP-4P-1.1", "rated_power")
        assert any(r.unit == "kW" for r in records), "kW unit not recorded"
