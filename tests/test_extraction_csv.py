"""
test_extraction_csv.py
=======================
Tests for the CSV extractor against the real legacy_motors.csv dataset.
"""
import pytest
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "data" / "csv" / "legacy_motors.csv"
MANIFEST_PATH = Path(__file__).parent.parent / "data" / "dataset_manifest.json"

EXPECTED_PRODUCTS = [
    "PIQ-W22SP-4P-1.1", "PIQ-W22SP-4P-1.5", "PIQ-W22SP-4P-2.2",
    "PIQ-W22SP-4P-3.0", "PIQ-W22SP-4P-4.0", "PIQ-W22SP-4P-5.5",
    "PIQ-W22SP-4P-7.5", "PIQ-W22SP-4P-9.2", "PIQ-W22SP-4P-11",
    "PIQ-W22SP-4P-15", "PIQ-W22SP-6P-0.75", "PIQ-W22SP-6P-1.1",
]


def _load_manifest():
    import json
    if not MANIFEST_PATH.exists():
        return {}
    with open(MANIFEST_PATH) as f:
        products = json.load(f)
    return {p["product_id"]: p for p in products}


@pytest.fixture(scope="module")
def csv_extractor():
    from productiq.extraction import CSVExtractor
    if not CSV_PATH.exists():
        pytest.skip(f"CSV not found: {CSV_PATH}")
    manifest = _load_manifest()
    return CSVExtractor(
        csv_path=CSV_PATH,
        source_id="legacy_motors_csv_weg_w22sp_derived",
        manifest_products=manifest,
    )


@pytest.fixture(scope="module")
def csv_results(csv_extractor):
    return csv_extractor.extract_all()


class TestCSVExtractorInit:
    def test_importable(self):
        from productiq.extraction import CSVExtractor
        assert CSVExtractor is not None

    def test_missing_csv_returns_failure(self):
        from productiq.extraction import CSVExtractor
        extractor = CSVExtractor(
            csv_path=Path("/nonexistent.csv"),
            source_id="test",
            manifest_products={},
        )
        results = extractor.extract_all()
        assert len(results) == 1
        assert results[0].succeeded is False

    def test_empty_manifest_still_extracts(self):
        from productiq.extraction import CSVExtractor
        if not CSV_PATH.exists():
            pytest.skip("CSV not available")
        extractor = CSVExtractor(
            csv_path=CSV_PATH,
            source_id="test",
            manifest_products={},
        )
        results = extractor.extract_all()
        # Should still produce results even without manifest match
        assert len(results) >= 1


class TestCSVResults:
    def test_returns_list(self, csv_results):
        assert isinstance(csv_results, list)

    def test_all_12_products_extracted(self, csv_results):
        assert len(csv_results) == 12, (
            f"Expected 12 product results, got {len(csv_results)}"
        )

    def test_all_known_product_ids_present(self, csv_results):
        extracted_pids = {r.product_id for r in csv_results}
        for pid in EXPECTED_PRODUCTS:
            assert pid in extracted_pids, f"Missing product: {pid}"

    def test_all_results_have_success_status(self, csv_results):
        from productiq.extraction.models import ExtractionStatus
        for r in csv_results:
            assert r.status == ExtractionStatus.SUCCESS.value, (
                f"{r.product_id} status={r.status}"
            )

    def test_each_result_has_evidence(self, csv_results):
        for r in csv_results:
            assert r.evidence_count > 0, f"{r.product_id} has no evidence"

    def test_all_results_source_type_csv(self, csv_results):
        for r in csv_results:
            assert r.source_type == "csv"


class TestCSVEvidenceProvenance:
    def test_all_evidence_has_row_number(self, csv_results):
        for result in csv_results:
            for e in result.evidence:
                assert e.row is not None, f"Missing row for {e.attribute}"
                assert e.row >= 1

    def test_all_evidence_has_column(self, csv_results):
        for result in csv_results:
            for e in result.evidence:
                assert e.column, f"Missing column name for {e.attribute}"

    def test_all_evidence_has_source_id(self, csv_results):
        for result in csv_results:
            for e in result.evidence:
                assert e.source_id == "legacy_motors_csv_weg_w22sp_derived"

    def test_all_evidence_has_raw_value(self, csv_results):
        for result in csv_results:
            for e in result.evidence:
                assert e.raw_value, f"Empty raw_value for {e.attribute}"

    def test_evidence_text_contains_row_context(self, csv_results):
        for result in csv_results[:3]:
            for e in result.evidence:
                assert len(e.evidence_text) > 0

    def test_product_id_not_extracted_as_spec(self, csv_results):
        for result in csv_results:
            for e in result.evidence:
                assert e.attribute != "product_id", (
                    "product_id should not appear as an evidence record"
                )


class TestCSVRepresentativeValues:
    def _get_records(self, csv_results, pid, attribute):
        for r in csv_results:
            if r.product_id == pid:
                return [e for e in r.evidence if e.attribute == attribute]
        return []

    def test_rated_power_extracted_for_1_1kw(self, csv_results):
        records = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "rated_power")
        assert records, "rated_power not extracted for PIQ-W22SP-4P-1.1"
        assert any(abs(r.value - 1.1) < 0.05 for r in records if r.value)

    def test_rated_current_extracted(self, csv_results):
        records = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "rated_current")
        assert records, "rated_current not extracted for PIQ-W22SP-4P-1.1"
        assert any(r.value is not None for r in records)

    def test_rated_speed_extracted(self, csv_results):
        records = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "rated_speed")
        assert records, "rated_speed not extracted"
        assert any(abs(r.value - 1455) < 10 for r in records if r.value)

    def test_efficiency_extracted(self, csv_results):
        records = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "efficiency")
        assert records, "efficiency not extracted"

    def test_weight_extracted(self, csv_results):
        records = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "weight")
        assert records, "weight not extracted"
        assert any(abs(r.value - 19.5) < 1.0 for r in records if r.value)

    def test_power_factor_extracted(self, csv_results):
        records = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "power_factor")
        assert records, "power_factor not extracted"
        assert any(abs(r.value - 0.59) < 0.05 for r in records if r.value)

    def test_frame_size_extracted(self, csv_results):
        records = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "frame_size")
        assert records, "frame_size not extracted"

    def test_units_correct(self, csv_results):
        power = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "rated_power")
        assert any(r.unit == "kW" for r in power)
        current = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "rated_current")
        assert any(r.unit == "A" for r in current)
        speed = self._get_records(csv_results, "PIQ-W22SP-4P-1.1", "rated_speed")
        assert any(r.unit == "rpm" for r in speed)

    def test_no_value_fabricated_for_empty_cell(self, csv_results):
        """Empty cells must not generate evidence records."""
        # All extracted records should have non-empty raw_value
        for result in csv_results:
            for e in result.evidence:
                assert e.raw_value.strip() != "", (
                    f"Empty raw_value found for {e.attribute} in {result.product_id}"
                )
