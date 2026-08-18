"""
test_extraction_contract.py
============================
Tests that EvidenceRecord and ExtractionResult fulfil the extraction contract:
  - every evidence record has provenance
  - source_type is a known value
  - product_id is preserved
  - model is serializable to dict and back
  - ExtractionResult.failure factory works correctly
"""
import json
import pytest
from productiq.extraction.models import (
    EvidenceRecord,
    ExtractionResult,
    ExtractionStatus,
    ExtractionMethod,
    BatchExtractionSummary,
)


class TestEvidenceRecord:
    def _sample(self) -> EvidenceRecord:
        return EvidenceRecord(
            source_id="test-src",
            source_type="pdf",
            product_id="PIQ-TEST-001",
            page=5,
            attribute="rated_power",
            raw_value="7.5",
            value=7.5,
            unit="kW",
            evidence_text="kW: 7.5 | rpm: 1465",
            method=ExtractionMethod.TABLE.value,
            confidence=0.92,
        )

    def test_instantiates(self):
        r = self._sample()
        assert r.source_id == "test-src"
        assert r.product_id == "PIQ-TEST-001"

    def test_source_type_preserved(self):
        r = self._sample()
        assert r.source_type in ("pdf", "web", "csv")

    def test_has_provenance(self):
        r = self._sample()
        assert r.source_id
        assert r.source_type
        assert r.product_id

    def test_pdf_provenance_has_page(self):
        r = self._sample()
        assert r.page == 5

    def test_csv_provenance_has_row_and_column(self):
        r = EvidenceRecord(
            source_id="csv-src",
            source_type="csv",
            product_id="PIQ-TEST-002",
            row=3,
            column="rated_power_kw",
            attribute="rated_power",
            raw_value="5.5",
            value=5.5,
            unit="kW",
            evidence_text="rated_power_kw=5.5",
            method=ExtractionMethod.COLUMN.value,
            confidence=0.85,
        )
        assert r.row == 3
        assert r.column == "rated_power_kw"

    def test_web_provenance_has_url(self):
        r = EvidenceRecord(
            source_id="web-src",
            source_type="web",
            product_id="PIQ-TEST-003",
            url="https://example.com/motor",
            attribute="rated_power",
            raw_value="1.1",
            value=1.1,
            unit="kW",
            evidence_text="Rated power: 1.1 kW",
            method=ExtractionMethod.HTML_TABLE.value,
            confidence=0.70,
        )
        assert r.url == "https://example.com/motor"

    def test_serialises_to_dict(self):
        r = self._sample()
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["source_id"] == "test-src"
        assert d["attribute"] == "rated_power"
        assert d["value"] == 7.5

    def test_round_trips_via_dict(self):
        r = self._sample()
        d = r.to_dict()
        r2 = EvidenceRecord.from_dict(d)
        assert r2.source_id == r.source_id
        assert r2.value == r.value
        assert r2.unit == r.unit

    def test_dict_is_json_serialisable(self):
        r = self._sample()
        json_str = json.dumps(r.to_dict())
        restored = json.loads(json_str)
        assert restored["product_id"] == "PIQ-TEST-001"


class TestExtractionResult:
    def _sample(self) -> ExtractionResult:
        evidence = [
            EvidenceRecord(
                source_id="src1",
                source_type="pdf",
                product_id="PIQ-TEST-001",
                page=5,
                attribute="rated_power",
                raw_value="1.1",
                value=1.1,
                unit="kW",
                evidence_text="...",
                method=ExtractionMethod.TABLE.value,
                confidence=0.9,
            )
        ]
        return ExtractionResult(
            source_id="src1",
            source_type="pdf",
            product_id="PIQ-TEST-001",
            status=ExtractionStatus.SUCCESS.value,
            evidence=evidence,
        )

    def test_instantiates(self):
        r = self._sample()
        assert r.source_id == "src1"
        assert r.status == ExtractionStatus.SUCCESS.value

    def test_evidence_count(self):
        r = self._sample()
        assert r.evidence_count == 1

    def test_succeeded_true_on_success(self):
        r = self._sample()
        assert r.succeeded is True

    def test_succeeded_false_on_failure(self):
        r = ExtractionResult.failure(
            source_id="x", source_type="web",
            product_id="PIQ-X", error="HTTP 403"
        )
        assert r.succeeded is False
        assert r.error == "HTTP 403"
        assert r.evidence_count == 0

    def test_failure_has_no_evidence(self):
        r = ExtractionResult.failure(
            source_id="x", source_type="pdf",
            product_id="PIQ-X", error="File not found"
        )
        assert len(r.evidence) == 0

    def test_serialises_to_json(self):
        r = self._sample()
        json_str = r.to_json()
        parsed = json.loads(json_str)
        assert parsed["product_id"] == "PIQ-TEST-001"
        assert len(parsed["evidence"]) == 1

    def test_dict_round_trip(self):
        r = self._sample()
        d = r.to_dict()
        assert d["status"] == ExtractionStatus.SUCCESS.value
        assert isinstance(d["evidence"], list)


class TestExtractionMethod:
    def test_all_methods_are_strings(self):
        for m in ExtractionMethod:
            assert isinstance(m.value, str)


class TestBatchSummary:
    def test_instantiates_with_zeros(self):
        s = BatchExtractionSummary()
        assert s.products_discovered == 0
        assert s.pdf_succeeded == 0

    def test_to_dict(self):
        s = BatchExtractionSummary(products_discovered=12, pdf_succeeded=10)
        d = s.to_dict()
        assert d["products_discovered"] == 12
        assert d["pdf_succeeded"] == 10
