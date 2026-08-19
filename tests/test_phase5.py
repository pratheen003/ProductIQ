"""
ProductIQ Phase 5 Test Suite — Trust-Aware Product Intelligence
===============================================================
Comprehensive test coverage for Phase 5 trust evaluation, review queue,
publishability decisions, conflict preservation, and deterministic scoring.
"""
import json
import pytest
from pathlib import Path

from productiq.schema.motor import MotorProduct, DataStatus, FieldValue, SourceEntry, CANONICAL_UNITS
from productiq.normalization.models import (
    NormalizedProduct,
    NormalizedField,
    NormalizationOutcome,
    ConflictRecord,
    EvidenceRef,
)
from productiq.validation.models import (
    ProductValidationReport,
    ValidationFinding,
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
    FindingEvidenceRef,
)
from productiq.enrichment.models import (
    ProductEnrichment,
    EnrichmentClaim,
)
from productiq.trust.models import (
    TrustStatus,
    PublishabilityStatus,
    AttributeTrustResult,
    ClaimTrustResult,
    ReviewItem,
    ProductTrustReport,
    BatchTrustReport,
)
from productiq.trust.evaluator import MotorTrustEvaluator
from productiq.trust.service import ProductTrustAnalyzer, BatchTrustAnalyzer


DEMO_PRODUCT_ID = "PIQ-W22SP-4P-1.1"


# ---------------------------------------------------------------------------
# 1. Pipeline Regression Tests
# ---------------------------------------------------------------------------

class TestPipelineRegression:
    def test_phase0_schema_intact(self):
        m = MotorProduct(product_id="TEST-1", manufacturer="WEG", model="W22")
        assert m.schema_version == "0.1.0-phase0"
        assert m.rated_power.status == DataStatus.UNKNOWN

    def test_phase1_evidence_contract(self):
        ref = EvidenceRef(
            source_id="pdf_brochure",
            source_type="pdf",
            product_id="TEST-1",
            attribute="rated_power",
            raw_value="1.1",
            raw_unit="kW",
            parsed_value=1.1,
            method="table",
            confidence=1.0,
            page=5,
        )
        assert ref.page == 5
        assert ref.to_dict()["source_type"] == "pdf"

    def test_phase2_normalization_models(self):
        field = NormalizedField(
            canonical_field="rated_power",
            canonical_unit="kW",
            canonical_value=1.1,
            outcome=NormalizationOutcome.PASSTHROUGH,
        )
        assert field.canonical_value == 1.1

    def test_phase3_validation_models(self):
        finding = ValidationFinding(
            rule_id="RANGE_RATED_POWER_POSITIVE",
            category=ValidationCategory.RANGE,
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            field="rated_power",
            description="Power must be positive",
            explanation="Valid positive power.",
        )
        report = ProductValidationReport(
            product_id="TEST-1",
            manufacturer="WEG",
            model="W22",
            findings=[finding],
        )
        assert report.pass_count == 1
        assert report.overall_status == ValidationStatus.PASS

    def test_phase4_enrichment_models(self):
        claim = EnrichmentClaim(
            claim_text="IE3 premium efficiency",
            category="performance",
            is_source_backed=True,
            confidence=1.0,
        )
        assert claim.is_source_backed is True


# ---------------------------------------------------------------------------
# 2. Trust Model & Enum Tests
# ---------------------------------------------------------------------------

class TestTrustModelsAndEnums:
    def test_trust_status_enum_values(self):
        assert TrustStatus.TRUSTED.value == "TRUSTED"
        assert TrustStatus.REVIEW_REQUIRED.value == "REVIEW_REQUIRED"
        assert TrustStatus.CONFLICTED.value == "CONFLICTED"
        assert TrustStatus.UNVERIFIED.value == "UNVERIFIED"
        assert TrustStatus.UNSUPPORTED.value == "UNSUPPORTED"
        assert TrustStatus.MISSING.value == "MISSING"

    def test_publishability_status_enum_values(self):
        assert PublishabilityStatus.PUBLISHABLE.value == "PUBLISHABLE"
        assert PublishabilityStatus.PUBLISHABLE_WITH_WARNING.value == "PUBLISHABLE_WITH_WARNING"
        assert PublishabilityStatus.REVIEW_REQUIRED.value == "REVIEW_REQUIRED"
        assert PublishabilityStatus.NOT_PUBLISHABLE.value == "NOT_PUBLISHABLE"

    def test_attribute_trust_result_round_trip(self):
        attr = AttributeTrustResult(
            field="rated_voltage",
            canonical_value=400.0,
            canonical_unit="V",
            trust_status=TrustStatus.TRUSTED,
            publishability=PublishabilityStatus.PUBLISHABLE,
            validation_status="PASS",
            is_conflicted=False,
            evidence_sources=["pdf:p.5"],
            confidence_score=1.0,
            reason="Verified from manufacturer datasheet.",
            validation_rule_ids=["RANGE_RATED_VOLTAGE_POSITIVE"],
        )
        d = attr.to_dict()
        assert d["trust_status"] == "TRUSTED"
        assert d["publishability"] == "PUBLISHABLE"
        rebuilt = AttributeTrustResult.from_dict(d)
        assert rebuilt.field == "rated_voltage"
        assert rebuilt.canonical_value == 400.0

    def test_claim_trust_result_round_trip(self):
        claim = ClaimTrustResult(
            claim_text="Operates with 4-pole synchronous speed",
            category="mechanical",
            claim_type="SOURCE_BACKED",
            trust_status=TrustStatus.TRUSTED,
            publishability=PublishabilityStatus.PUBLISHABLE,
            supporting_fields=["rated_speed", "poles"],
            evidence_sources=["pdf:p.5"],
            confidence=1.0,
            reason="Backed by datasheet electrical table.",
        )
        d = claim.to_dict()
        assert d["claim_type"] == "SOURCE_BACKED"
        rebuilt = ClaimTrustResult.from_dict(d)
        assert rebuilt.claim_text == claim.claim_text

    def test_review_item_round_trip(self):
        rev = ReviewItem(
            review_id="REV-TEST-rated_current",
            target_type="attribute",
            target_name="rated_current",
            severity="HIGH",
            issue_type="CONFLICT",
            description="PDF reports 2.34 A vs CSV reports 7.22 A.",
            validation_rule_id="CONFLICT_RATED_CURRENT_PDF_VS_CSV",
            recommended_action="Inspect physical nameplate.",
        )
        d = rev.to_dict()
        assert d["severity"] == "HIGH"
        rebuilt = ReviewItem.from_dict(d)
        assert rebuilt.review_id == "REV-TEST-rated_current"

    def test_batch_trust_report_round_trip(self):
        batch = BatchTrustReport(
            total_products=12,
            trusted_count=5,
            review_required_count=2,
            conflicted_count=5,
            publishable_count=5,
            publishable_with_warning_count=2,
            not_publishable_count=0,
            avg_trust_score=0.75,
            total_review_items=15,
            products=[],
        )
        d = batch.to_dict()
        assert d["total_products"] == 12
        assert d["avg_trust_score"] == 0.75


# ---------------------------------------------------------------------------
# 3. Attribute Trust Classification Tests
# ---------------------------------------------------------------------------

class TestAttributeTrustClassification:
    @pytest.fixture
    def evaluator(self):
        return MotorTrustEvaluator()

    def test_trusted_attribute(self, evaluator):
        ref = EvidenceRef(
            source_id="pdf", source_type="pdf", product_id="P1", attribute="rated_voltage",
            raw_value="400", raw_unit="V", parsed_value=400.0, method="table", confidence=1.0
        )
        field = NormalizedField(
            canonical_field="rated_voltage", canonical_unit="V", canonical_value=400.0,
            outcome=NormalizationOutcome.PASSTHROUGH, evidence_refs=[ref]
        )
        norm = NormalizedProduct(product_id="P1", manufacturer="WEG", model="W22", fields={"rated_voltage": field})
        finding = ValidationFinding(
            rule_id="RANGE_RATED_VOLTAGE_POSITIVE", category=ValidationCategory.RANGE,
            status=ValidationStatus.PASS, severity=ValidationSeverity.INFO, field="rated_voltage",
            description="Voltage check",
        )
        val = ProductValidationReport(product_id="P1", manufacturer="WEG", model="W22", findings=[finding])

        report = evaluator.evaluate(norm, val, product_id="P1")
        voltage_res = report.attribute_trust["rated_voltage"]
        assert voltage_res.trust_status == TrustStatus.TRUSTED
        assert voltage_res.publishability == PublishabilityStatus.PUBLISHABLE
        assert voltage_res.canonical_value == 400.0
        assert voltage_res.confidence_score == 1.0

    def test_conflicted_attribute(self, evaluator):
        ref_a = EvidenceRef(source_id="pdf", source_type="pdf", product_id="P1", attribute="rated_current", raw_value="2.34", raw_unit="A", parsed_value=2.34, method="table", confidence=1.0)
        ref_b = EvidenceRef(source_id="csv", source_type="csv", product_id="P1", attribute="rated_current", raw_value="7.22", raw_unit="A", parsed_value=7.22, method="column", confidence=1.0)
        conflict = ConflictRecord(canonical_field="rated_current", value_a=2.34, unit_a="A", source_a=ref_a, value_b=7.22, unit_b="A", source_b=ref_b)
        field = NormalizedField(canonical_field="rated_current", canonical_unit="A", canonical_value=None, outcome=NormalizationOutcome.CONFLICT, conflicts=[conflict], evidence_refs=[ref_a, ref_b])
        norm = NormalizedProduct(product_id="P1", manufacturer="WEG", model="W22", fields={"rated_current": field})

        finding = ValidationFinding(
            rule_id="CONFLICT_RATED_CURRENT_PDF_VS_CSV", category=ValidationCategory.CONFLICT,
            status=ValidationStatus.CONFLICT, severity=ValidationSeverity.HIGH, field="rated_current",
            description="Conflict check",
            explanation="PDF 2.34 A vs CSV 7.22 A."
        )
        val = ProductValidationReport(product_id="P1", manufacturer="WEG", model="W22", findings=[finding])

        report = evaluator.evaluate(norm, val, product_id="P1")
        current_res = report.attribute_trust["rated_current"]
        assert current_res.trust_status == TrustStatus.CONFLICTED
        assert current_res.publishability == PublishabilityStatus.REVIEW_REQUIRED
        assert current_res.canonical_value is None
        assert current_res.is_conflicted is True

    def test_inferred_attribute_from_enrichment(self, evaluator):
        norm = NormalizedProduct(product_id="P1", manufacturer="WEG", model="W22", fields={})
        val = ProductValidationReport(product_id="P1", manufacturer="WEG", model="W22", findings=[])
        enrich = ProductEnrichment(
            product_id="P1", manufacturer="WEG", model="W22",
            summary="Test summary", technical_description="Desc",
            inferred_fields={"frequency": "50 Hz"}
        )

        report = evaluator.evaluate(norm, val, enrichment=enrich, product_id="P1")
        freq_res = report.attribute_trust["frequency"]
        assert freq_res.trust_status == TrustStatus.UNVERIFIED
        assert freq_res.publishability == PublishabilityStatus.PUBLISHABLE_WITH_WARNING
        assert freq_res.canonical_value == "50 Hz"
        assert freq_res.confidence_score == 0.70

    def test_missing_attribute(self, evaluator):
        norm = NormalizedProduct(product_id="P1", manufacturer="WEG", model="W22", fields={})
        val = ProductValidationReport(product_id="P1", manufacturer="WEG", model="W22", findings=[])

        report = evaluator.evaluate(norm, val, product_id="P1")
        weight_res = report.attribute_trust["weight"]
        assert weight_res.trust_status == TrustStatus.MISSING
        assert weight_res.publishability == PublishabilityStatus.NOT_PUBLISHABLE
        assert weight_res.canonical_value is None
        assert weight_res.confidence_score == 0.0

    def test_failed_validation_attribute(self, evaluator):
        ref = EvidenceRef(source_id="pdf", source_type="pdf", product_id="P1", attribute="efficiency", raw_value="150.0", raw_unit="%", parsed_value=150.0, method="table", confidence=1.0)
        field = NormalizedField(canonical_field="efficiency", canonical_unit="%", canonical_value=150.0, outcome=NormalizationOutcome.PASSTHROUGH, evidence_refs=[ref])
        norm = NormalizedProduct(product_id="P1", manufacturer="WEG", model="W22", fields={"efficiency": field})

        finding = ValidationFinding(
            rule_id="RANGE_EFFICIENCY_BOUNDS", category=ValidationCategory.RANGE,
            status=ValidationStatus.FAIL, severity=ValidationSeverity.CRITICAL, field="efficiency",
            description="Efficiency bounds check",
            explanation="Efficiency 150% exceeds maximum 100%."
        )
        val = ProductValidationReport(product_id="P1", manufacturer="WEG", model="W22", findings=[finding])

        report = evaluator.evaluate(norm, val, product_id="P1")
        eff_res = report.attribute_trust["efficiency"]
        assert eff_res.trust_status == TrustStatus.UNSUPPORTED
        assert eff_res.publishability == PublishabilityStatus.NOT_PUBLISHABLE


# ---------------------------------------------------------------------------
# 4. Claim Trust Classification Tests
# ---------------------------------------------------------------------------

class TestClaimTrustClassification:
    @pytest.fixture
    def evaluator(self):
        return MotorTrustEvaluator()

    def test_source_backed_claim_trusted(self, evaluator):
        norm = NormalizedProduct(product_id="P1", manufacturer="WEG", model="W22", fields={})
        val = ProductValidationReport(product_id="P1", manufacturer="WEG", model="W22", findings=[])
        claim = EnrichmentClaim(
            claim_text="Delivers 1.1 kW rated power",
            category="performance",
            field="rated_power",
            is_source_backed=True,
            evidence_sources=["pdf:p.5"],
            confidence=1.0,
        )
        enrich = ProductEnrichment(
            product_id="P1", manufacturer="WEG", model="W22",
            summary="Sum", technical_description="Desc",
            source_backed_claims=[claim],
        )

        report = evaluator.evaluate(norm, val, enrichment=enrich, product_id="P1")
        assert len(report.claim_trust) == 1
        c_res = report.claim_trust[0]
        assert c_res.trust_status == TrustStatus.TRUSTED
        assert c_res.publishability == PublishabilityStatus.PUBLISHABLE
        assert c_res.claim_type == "SOURCE_BACKED"

    def test_source_backed_claim_with_conflicted_field(self, evaluator):
        ref_a = EvidenceRef(source_id="pdf", source_type="pdf", product_id="P1", attribute="rated_current", raw_value="2.34", raw_unit="A", parsed_value=2.34, method="table", confidence=1.0)
        ref_b = EvidenceRef(source_id="csv", source_type="csv", product_id="P1", attribute="rated_current", raw_value="7.22", raw_unit="A", parsed_value=7.22, method="column", confidence=1.0)
        conflict = ConflictRecord(canonical_field="rated_current", value_a=2.34, unit_a="A", source_a=ref_a, value_b=7.22, unit_b="A", source_b=ref_b)
        field = NormalizedField(canonical_field="rated_current", canonical_unit="A", canonical_value=None, outcome=NormalizationOutcome.CONFLICT, conflicts=[conflict])
        norm = NormalizedProduct(product_id="P1", manufacturer="WEG", model="W22", fields={"rated_current": field})
        val = ProductValidationReport(product_id="P1", manufacturer="WEG", model="W22", findings=[])

        claim = EnrichmentClaim(
            claim_text="Draws 2.34 A full-load current",
            category="electrical",
            field="rated_current",
            is_source_backed=True,
            evidence_sources=["pdf:p.5"],
            confidence=1.0,
        )
        enrich = ProductEnrichment(
            product_id="P1", manufacturer="WEG", model="W22",
            summary="Sum", technical_description="Desc",
            source_backed_claims=[claim],
        )

        report = evaluator.evaluate(norm, val, enrichment=enrich, product_id="P1")
        c_res = report.claim_trust[0]
        assert c_res.trust_status == TrustStatus.CONFLICTED
        assert c_res.publishability == PublishabilityStatus.REVIEW_REQUIRED


# ---------------------------------------------------------------------------
# 5. Dedicated Hard-Gate: Known Conflict (PIQ-W22SP-4P-1.1)
# ---------------------------------------------------------------------------

class TestKnownConflictPreservation:
    def test_known_conflict_rated_current_on_real_data(self):
        analyzer = ProductTrustAnalyzer()
        report = analyzer.analyze(DEMO_PRODUCT_ID, data_dir="data", save_output=False)

        assert report.product_id == DEMO_PRODUCT_ID
        assert report.overall_trust_status == TrustStatus.CONFLICTED
        assert report.overall_publishability == PublishabilityStatus.REVIEW_REQUIRED

        current_attr = report.attribute_trust["rated_current"]
        assert current_attr.trust_status == TrustStatus.CONFLICTED
        assert current_attr.publishability == PublishabilityStatus.REVIEW_REQUIRED
        assert current_attr.canonical_value is None
        assert current_attr.is_conflicted is True

        # Check evidence provenance exists
        assert len(current_attr.evidence_sources) >= 2
        # Check review item exists
        rev_item = next((r for r in report.review_queue if r.target_name == "rated_current"), None)
        assert rev_item is not None
        assert rev_item.issue_type == "CONFLICT"
        assert rev_item.severity == "HIGH"
        assert len(rev_item.conflicting_values) >= 1
        assert "recommended_action" in rev_item.to_dict()


# ---------------------------------------------------------------------------
# 6. Dedicated Test: Clean Publishable Attribute
# ---------------------------------------------------------------------------

class TestCleanPublishableAttribute:
    def test_clean_publishable_attribute_on_real_data(self):
        analyzer = ProductTrustAnalyzer()
        report = analyzer.analyze(DEMO_PRODUCT_ID, data_dir="data", save_output=False)

        voltage_attr = report.attribute_trust["rated_voltage"]
        assert voltage_attr.trust_status == TrustStatus.TRUSTED
        assert voltage_attr.publishability == PublishabilityStatus.PUBLISHABLE
        assert voltage_attr.canonical_value == 400.0
        assert voltage_attr.confidence_score == 1.0
        assert len(voltage_attr.evidence_sources) >= 1

        assert "rated_voltage" in report.publishable_attributes
        assert "rated_current" in report.restricted_attributes


# ---------------------------------------------------------------------------
# 7. Review Queue & Deterministic Scoring
# ---------------------------------------------------------------------------

class TestReviewQueueAndScoring:
    def test_review_queue_generation_for_real_product(self):
        analyzer = ProductTrustAnalyzer()
        report = analyzer.analyze(DEMO_PRODUCT_ID, data_dir="data", save_output=False)

        assert len(report.review_queue) > 0
        for item in report.review_queue:
            assert item.review_id.startswith("REV-")
            assert item.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            assert item.recommended_action != ""

    def test_trust_score_determinism(self):
        analyzer = ProductTrustAnalyzer()
        report1 = analyzer.analyze(DEMO_PRODUCT_ID, data_dir="data", save_output=False)
        report2 = analyzer.analyze(DEMO_PRODUCT_ID, data_dir="data", save_output=False)

        assert report1.trust_score == report2.trust_score
        assert report1.trust_score_formula == report2.trust_score_formula
        assert report1.trust_score_breakdown == report2.trust_score_breakdown


# ---------------------------------------------------------------------------
# 8. Real Dataset Batch Execution
# ---------------------------------------------------------------------------

class TestBatchDatasetExecution:
    def test_batch_trust_analyzer_executes_all_12_products(self):
        analyzer = BatchTrustAnalyzer()
        batch_report = analyzer.analyze_dataset(data_dir="data", save_output=False)

        assert batch_report.total_products == 12
        assert len(batch_report.products) == 12
        assert batch_report.avg_trust_score > 0.0
        assert batch_report.total_review_items > 0
