"""
test_phase3.py
==============
Phase 3 integration tests — real data, all 12 products.

Covers:
- Phase 0/1/2 regression
- Validation modules import
- Models serialize/deserialize
- Schema validation rules work
- Required-field rules work
- Range rules (valid and invalid values)
- Cross-source conflict detection
- Known real conflict (2.34 A vs 7.22 A) explicitly detected
- Engineering plausibility checks
- Provenance preserved through validation
- All 12 products validated
- Validation output files exist
- No fabricated values
- Deterministic behavior
"""
import json
import math
from pathlib import Path
from typing import Optional

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFEST_PATH = DATA_DIR / "dataset_manifest.json"

PRODUCT_IDS = [
    "PIQ-W22SP-4P-1.1",
    "PIQ-W22SP-4P-1.5",
    "PIQ-W22SP-4P-2.2",
    "PIQ-W22SP-4P-3.0",
    "PIQ-W22SP-4P-4.0",
    "PIQ-W22SP-4P-5.5",
    "PIQ-W22SP-4P-7.5",
    "PIQ-W22SP-4P-9.2",
    "PIQ-W22SP-4P-11",
    "PIQ-W22SP-4P-15",
    "PIQ-W22SP-6P-0.75",
    "PIQ-W22SP-6P-1.1",
]

DEMO_PRODUCT_ID = "PIQ-W22SP-4P-1.1"  # Primary demo product for known conflict


# ---------------------------------------------------------------------------
# Phase 0 regression
# ---------------------------------------------------------------------------

class TestPhase0Regression:
    def test_schema_imports(self):
        from productiq.schema import CANONICAL_UNITS, DataStatus, FieldValue, MotorProduct
        assert len(CANONICAL_UNITS) == 11
        assert {s.value for s in DataStatus} == {"Verified", "Inferred", "Conflicted", "Unknown"}

    def test_schema_version_frozen(self):
        from productiq.schema import MotorProduct
        p = MotorProduct(product_id="t", manufacturer="t", model="t")
        assert p.schema_version == "0.1.0-phase0"

    def test_four_tier_enum(self):
        from productiq.schema import DataStatus
        assert len(DataStatus) == 4


# ---------------------------------------------------------------------------
# Phase 2 regression
# ---------------------------------------------------------------------------

class TestPhase2Regression:
    def test_normalization_imports(self):
        from productiq.normalization import MotorNormalizer, NormalizedProduct, NormalizationOutcome
        assert MotorNormalizer is not None

    def test_normalized_output_exists(self):
        for pid in PRODUCT_IDS:
            path = PROCESSED_DIR / pid / "normalized_product.json"
            assert path.exists(), f"normalized_product.json missing for {pid}"


# ---------------------------------------------------------------------------
# Phase 3 module imports
# ---------------------------------------------------------------------------

class TestPhase3Imports:
    def test_validation_package_imports(self):
        from productiq.validation import (
            BatchValidator, MotorValidator,
            ProductValidationReport, ValidationFinding,
            ValidationStatus, ValidationSeverity, ValidationCategory,
        )
        assert MotorValidator is not None
        assert BatchValidator is not None

    def test_models_import(self):
        from productiq.validation.models import (
            ValidationStatus, ValidationSeverity, ValidationCategory,
            ValidationFinding, ProductValidationReport, BatchValidationReport,
            FindingEvidenceRef,
        )
        assert ValidationStatus.PASS is not None
        assert ValidationStatus.CONFLICT is not None

    def test_rules_import(self):
        from productiq.validation.rules import (
            check_schema_canonical_units,
            check_required_fields,
            check_range_rated_power,
            check_cross_source_consistency,
            check_engineering_torque_power_rpm,
            check_known_current_conflict,
        )
        assert check_schema_canonical_units is not None

    def test_validator_import(self):
        from productiq.validation.validator import MotorValidator, BatchValidator
        assert MotorValidator is not None


# ---------------------------------------------------------------------------
# Model serialization
# ---------------------------------------------------------------------------

class TestModelSerialization:
    def test_finding_serializes(self):
        from productiq.validation.models import (
            ValidationFinding, ValidationStatus, ValidationSeverity, ValidationCategory,
        )
        f = ValidationFinding(
            rule_id="TEST_RULE",
            category=ValidationCategory.RANGE,
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            field="rated_power",
            description="Test rule",
            actual_value=1.1,
            actual_unit="kW",
            expected_condition="> 0",
            explanation="Test explanation.",
        )
        d = f.to_dict()
        assert d["rule_id"] == "TEST_RULE"
        assert d["status"] == "PASS"
        assert d["actual_value"] == 1.1

    def test_product_report_serializes(self):
        from productiq.validation.models import (
            ProductValidationReport, ValidationStatus,
        )
        report = ProductValidationReport(
            product_id="TEST-001",
            manufacturer="WEG",
            model="W22 Test",
        )
        d = report.to_dict()
        assert d["product_id"] == "TEST-001"
        assert "summary" in d
        assert "findings" in d

    def test_report_json_round_trip(self):
        from productiq.validation.models import ProductValidationReport
        report = ProductValidationReport(
            product_id="TEST-001",
            manufacturer="WEG",
            model="W22 Test",
        )
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["product_id"] == "TEST-001"

    def test_evidence_ref_serializes(self):
        from productiq.validation.models import FindingEvidenceRef
        ref = FindingEvidenceRef(
            source_id="test_source",
            source_type="pdf",
            attribute="rated_current",
            raw_value="2.34",
            raw_unit="A",
            page=5,
        )
        d = ref.to_dict()
        assert d["source_type"] == "pdf"
        assert d["raw_value"] == "2.34"


# ---------------------------------------------------------------------------
# Schema validation rules
# ---------------------------------------------------------------------------

class TestSchemaRules:
    def _make_normalized_product_with_field(self, field_name, canonical_unit, value=1.0):
        """Build a minimal NormalizedProduct with one field for testing."""
        from productiq.normalization.models import (
            NormalizedProduct, NormalizedField, NormalizationOutcome,
        )
        nf = NormalizedField(
            canonical_field=field_name,
            canonical_unit=canonical_unit,
            canonical_value=value,
            outcome=NormalizationOutcome.PASSTHROUGH,
        )
        return NormalizedProduct(
            product_id="TEST-001",
            manufacturer="WEG",
            model="W22",
            fields={field_name: nf},
        )

    def test_correct_unit_passes(self):
        from productiq.validation.rules import check_schema_canonical_units
        product = self._make_normalized_product_with_field("rated_power", "kW", 1.1)
        findings = check_schema_canonical_units(product)
        assert any(f.status.value == "PASS" for f in findings)

    def test_wrong_unit_fails(self):
        from productiq.validation.rules import check_schema_canonical_units
        # Use wrong unit for rated_power
        product = self._make_normalized_product_with_field("rated_power", "W", 1100.0)
        findings = check_schema_canonical_units(product)
        assert any(f.status.value == "FAIL" for f in findings)

    def test_dimensionless_field_correct(self):
        from productiq.validation.rules import check_schema_canonical_units
        # power_factor should have unit=None
        product = self._make_normalized_product_with_field("power_factor", None, 0.8)
        findings = check_schema_canonical_units(product)
        assert any(f.status.value == "PASS" for f in findings)

    def test_normalization_version_pass(self):
        from productiq.validation.rules import check_schema_normalization_version
        from productiq.normalization.models import NormalizedProduct
        product = NormalizedProduct(product_id="T", manufacturer="T", model="T",
                                    normalization_version="2.0.0")
        findings = check_schema_normalization_version(product)
        assert findings[0].status.value == "PASS"

    def test_wrong_normalization_version_warns(self):
        from productiq.validation.rules import check_schema_normalization_version
        from productiq.normalization.models import NormalizedProduct
        product = NormalizedProduct(product_id="T", manufacturer="T", model="T",
                                    normalization_version="1.0.0")
        findings = check_schema_normalization_version(product)
        assert findings[0].status.value == "WARNING"


# ---------------------------------------------------------------------------
# Required-field validation
# ---------------------------------------------------------------------------

class TestRequiredFieldRules:
    def _empty_product(self) -> "NormalizedProduct":
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        from productiq.schema import CANONICAL_UNITS
        fields = {
            fname: NormalizedField(
                canonical_field=fname,
                canonical_unit=CANONICAL_UNITS.get(fname),
                canonical_value=None,
                outcome=NormalizationOutcome.MISSING,
            )
            for fname in CANONICAL_UNITS
        }
        return NormalizedProduct(
            product_id="EMPTY-001", manufacturer="WEG", model="W22",
            fields=fields,
        )

    def _product_with_power(self) -> "NormalizedProduct":
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        from productiq.schema import CANONICAL_UNITS
        fields = {
            fname: NormalizedField(
                canonical_field=fname,
                canonical_unit=CANONICAL_UNITS.get(fname),
                canonical_value=None,
                outcome=NormalizationOutcome.MISSING,
            )
            for fname in CANONICAL_UNITS
        }
        fields["rated_power"].canonical_value = 1.1
        fields["rated_power"].outcome = NormalizationOutcome.PASSTHROUGH
        fields["rated_voltage"].canonical_value = 400.0
        fields["rated_voltage"].outcome = NormalizationOutcome.PASSTHROUGH
        fields["rated_speed"].canonical_value = 1455.0
        fields["rated_speed"].outcome = NormalizationOutcome.PASSTHROUGH
        return NormalizedProduct(
            product_id="FULL-001", manufacturer="WEG", model="W22",
            fields=fields,
        )

    def test_missing_required_fields_fail(self):
        from productiq.validation.rules import check_required_fields
        product = self._empty_product()
        findings = check_required_fields(product)
        fail_findings = [f for f in findings if f.status.value == "FAIL"]
        assert len(fail_findings) == 3  # rated_power, rated_voltage, rated_speed

    def test_present_required_fields_pass(self):
        from productiq.validation.rules import check_required_fields
        product = self._product_with_power()
        findings = check_required_fields(product)
        pass_findings = [f for f in findings if f.status.value == "PASS"]
        assert len(pass_findings) == 3


# ---------------------------------------------------------------------------
# Range validation rules
# ---------------------------------------------------------------------------

class TestRangeRules:
    def _product_with_one_field(self, field_name, value, unit=None):
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        nf = NormalizedField(
            canonical_field=field_name,
            canonical_unit=unit,
            canonical_value=value,
            outcome=NormalizationOutcome.PASSTHROUGH,
        )
        return NormalizedProduct(
            product_id="T", manufacturer="T", model="T",
            fields={field_name: nf},
        )

    def test_positive_power_passes(self):
        from productiq.validation.rules import check_range_rated_power
        product = self._product_with_one_field("rated_power", 1.1, "kW")
        findings = check_range_rated_power(product)
        assert findings[0].status.value == "PASS"

    def test_zero_power_fails(self):
        from productiq.validation.rules import check_range_rated_power
        product = self._product_with_one_field("rated_power", 0.0, "kW")
        findings = check_range_rated_power(product)
        assert findings[0].status.value == "FAIL"

    def test_negative_power_fails(self):
        from productiq.validation.rules import check_range_rated_power
        product = self._product_with_one_field("rated_power", -1.0, "kW")
        findings = check_range_rated_power(product)
        assert findings[0].status.value == "FAIL"

    def test_valid_voltage_passes(self):
        from productiq.validation.rules import check_range_rated_voltage
        product = self._product_with_one_field("rated_voltage", 400.0, "V")
        findings = check_range_rated_voltage(product)
        assert findings[0].status.value == "PASS"

    def test_valid_efficiency_passes(self):
        from productiq.validation.rules import check_range_efficiency
        product = self._product_with_one_field("efficiency", 84.8, "%")
        findings = check_range_efficiency(product)
        assert findings[0].status.value == "PASS"

    def test_over_100_efficiency_fails(self):
        from productiq.validation.rules import check_range_efficiency
        product = self._product_with_one_field("efficiency", 101.0, "%")
        findings = check_range_efficiency(product)
        assert findings[0].status.value == "FAIL"

    def test_negative_efficiency_fails(self):
        from productiq.validation.rules import check_range_efficiency
        product = self._product_with_one_field("efficiency", -5.0, "%")
        findings = check_range_efficiency(product)
        assert findings[0].status.value == "FAIL"

    def test_valid_power_factor_passes(self):
        from productiq.validation.rules import check_range_power_factor
        product = self._product_with_one_field("power_factor", 0.80)
        findings = check_range_power_factor(product)
        assert findings[0].status.value == "PASS"

    def test_pf_above_1_fails(self):
        from productiq.validation.rules import check_range_power_factor
        product = self._product_with_one_field("power_factor", 1.5)
        findings = check_range_power_factor(product)
        assert findings[0].status.value == "FAIL"

    def test_pf_negative_fails(self):
        from productiq.validation.rules import check_range_power_factor
        product = self._product_with_one_field("power_factor", -0.1)
        findings = check_range_power_factor(product)
        assert findings[0].status.value == "FAIL"

    def test_missing_field_not_checked(self):
        from productiq.validation.rules import check_range_rated_power
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        nf = NormalizedField(canonical_field="rated_power", canonical_unit="kW",
                             canonical_value=None, outcome=NormalizationOutcome.MISSING)
        product = NormalizedProduct(product_id="T", manufacturer="T", model="T",
                                    fields={"rated_power": nf})
        findings = check_range_rated_power(product)
        assert findings[0].status.value == "NOT_CHECKED"

    def test_valid_weight_passes(self):
        from productiq.validation.rules import check_range_weight
        product = self._product_with_one_field("weight", 19.5, "kg")
        findings = check_range_weight(product)
        assert findings[0].status.value == "PASS"

    def test_zero_weight_fails(self):
        from productiq.validation.rules import check_range_weight
        product = self._product_with_one_field("weight", 0.0, "kg")
        findings = check_range_weight(product)
        assert findings[0].status.value == "FAIL"


# ---------------------------------------------------------------------------
# Cross-source consistency (conflict detection)
# ---------------------------------------------------------------------------

class TestCrossSourceConsistency:
    def _product_with_conflict(self, field_name, val_a, val_b, src_type_a="pdf", src_type_b="csv"):
        from productiq.normalization.models import (
            NormalizedProduct, NormalizedField, NormalizationOutcome,
            ConflictRecord, EvidenceRef,
        )
        ref_a = EvidenceRef(
            source_id="src_a", source_type=src_type_a, product_id="T",
            attribute=field_name, raw_value=str(val_a), raw_unit="A",
            parsed_value=val_a, method="table", confidence=0.9,
        )
        ref_b = EvidenceRef(
            source_id="src_b", source_type=src_type_b, product_id="T",
            attribute=field_name, raw_value=str(val_b), raw_unit="A",
            parsed_value=val_b, method="column", confidence=0.85,
        )
        conflict = ConflictRecord(
            canonical_field=field_name,
            value_a=val_a, unit_a="A", source_a=ref_a,
            value_b=val_b, unit_b="A", source_b=ref_b,
            note=f"Conflict: {val_a} vs {val_b}",
        )
        nf = NormalizedField(
            canonical_field=field_name,
            canonical_unit="A",
            canonical_value=None,
            outcome=NormalizationOutcome.CONFLICT,
            evidence_refs=[ref_a, ref_b],
            conflicts=[conflict],
        )
        return NormalizedProduct(
            product_id="T", manufacturer="WEG", model="W22",
            fields={field_name: nf},
        )

    def test_conflict_detected(self):
        from productiq.validation.rules import check_cross_source_consistency
        product = self._product_with_conflict("rated_current", 2.34, 7.22)
        findings = check_cross_source_consistency(product)
        assert len(findings) == 1
        assert findings[0].status.value == "CONFLICT"

    def test_conflict_preserves_both_values(self):
        from productiq.validation.rules import check_cross_source_consistency
        product = self._product_with_conflict("rated_current", 2.34, 7.22)
        findings = check_cross_source_consistency(product)
        assert "2.34" in findings[0].explanation
        assert "7.22" in findings[0].explanation

    def test_conflict_preserves_provenance(self):
        from productiq.validation.rules import check_cross_source_consistency
        product = self._product_with_conflict("rated_current", 2.34, 7.22)
        findings = check_cross_source_consistency(product)
        assert len(findings[0].evidence_refs) == 2

    def test_no_conflict_no_findings(self):
        from productiq.validation.rules import check_cross_source_consistency
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        nf = NormalizedField(
            canonical_field="rated_voltage", canonical_unit="V",
            canonical_value=400.0, outcome=NormalizationOutcome.PASSTHROUGH,
        )
        product = NormalizedProduct(
            product_id="T", manufacturer="WEG", model="W22",
            fields={"rated_voltage": nf},
        )
        findings = check_cross_source_consistency(product)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# Known real conflict: 2.34 A (PDF) vs 7.22 A (CSV)
# ---------------------------------------------------------------------------

class TestKnownConflictDetection:
    """HARD GATE: The known PDF/CSV rated_current conflict must be detected."""

    @pytest.fixture(scope="class")
    def demo_report(self):
        path = PROCESSED_DIR / DEMO_PRODUCT_ID / "validation_report.json"
        if not path.exists():
            pytest.skip(f"validation_report.json not found for {DEMO_PRODUCT_ID}")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_known_conflict_rule_fires(self, demo_report):
        """CONFLICT_RATED_CURRENT_PDF_VS_CSV rule must fire for the demo product."""
        rule_ids = [f["rule_id"] for f in demo_report["findings"]]
        assert "CONFLICT_RATED_CURRENT_PDF_VS_CSV" in rule_ids, (
            "HARD GATE FAILED: CONFLICT_RATED_CURRENT_PDF_VS_CSV not in findings. "
            "The known 2.34A (PDF) vs 7.22A (CSV) conflict was not detected."
        )

    def test_known_conflict_is_conflict_status(self, demo_report):
        """The conflict finding must have status=CONFLICT."""
        conflict_finding = next(
            (f for f in demo_report["findings"]
             if f["rule_id"] == "CONFLICT_RATED_CURRENT_PDF_VS_CSV"),
            None,
        )
        assert conflict_finding is not None
        assert conflict_finding["status"] == "CONFLICT", (
            "CONFLICT_RATED_CURRENT_PDF_VS_CSV must have status=CONFLICT."
        )

    def test_known_conflict_preserves_pdf_value(self, demo_report):
        """PDF value 2.34 A must be preserved in the conflict finding."""
        conflict_finding = next(
            (f for f in demo_report["findings"]
             if f["rule_id"] == "CONFLICT_RATED_CURRENT_PDF_VS_CSV"),
            None,
        )
        assert conflict_finding is not None
        assert "2.34" in conflict_finding["explanation"], (
            "PDF value 2.34 A must appear in the conflict explanation."
        )

    def test_known_conflict_preserves_csv_value(self, demo_report):
        """CSV value 7.22 A must be preserved in the conflict finding."""
        conflict_finding = next(
            (f for f in demo_report["findings"]
             if f["rule_id"] == "CONFLICT_RATED_CURRENT_PDF_VS_CSV"),
            None,
        )
        assert conflict_finding is not None
        assert "7.22" in conflict_finding["explanation"], (
            "CSV value 7.22 A must appear in the conflict explanation."
        )

    def test_conflict_has_evidence_refs(self, demo_report):
        """Both evidence sources must be referenced in the conflict finding."""
        conflict_finding = next(
            (f for f in demo_report["findings"]
             if f["rule_id"] == "CONFLICT_RATED_CURRENT_PDF_VS_CSV"),
            None,
        )
        assert conflict_finding is not None
        assert len(conflict_finding["evidence_refs"]) >= 2, (
            "Conflict finding must reference both evidence sources (PDF and CSV)."
        )

    def test_conflict_not_silently_resolved(self, demo_report):
        """The rated_current field must not have a canonical_value in the normalized product."""
        norm_path = PROCESSED_DIR / DEMO_PRODUCT_ID / "normalized_product.json"
        if not norm_path.exists():
            pytest.skip("normalized_product.json not found")
        norm_data = json.loads(norm_path.read_text(encoding="utf-8"))
        rc = norm_data["fields"]["rated_current"]
        assert rc["canonical_value"] is None, (
            "rated_current must have canonical_value=None when conflicted — "
            "Phase 2/3 must not silently pick a winner."
        )

    def test_overall_status_is_conflict(self, demo_report):
        """Product with known conflict must have overall_status=CONFLICT."""
        assert demo_report["overall_status"] == "CONFLICT", (
            f"Expected overall_status=CONFLICT, got {demo_report['overall_status']}"
        )


# ---------------------------------------------------------------------------
# Engineering rules
# ---------------------------------------------------------------------------

class TestEngineeringRules:
    def _product_for_torque(self, power_kw, speed_rpm, torque_nm):
        from productiq.normalization.models import (
            NormalizedProduct, NormalizedField, NormalizationOutcome, EvidenceRef,
        )
        p_ref = EvidenceRef(source_id="s", source_type="pdf", product_id="T",
                            attribute="rated_power", raw_value=str(power_kw), raw_unit="kW",
                            parsed_value=power_kw, method="table", confidence=0.9)
        n_ref = EvidenceRef(source_id="s", source_type="pdf", product_id="T",
                            attribute="rated_speed", raw_value=str(speed_rpm), raw_unit="rpm",
                            parsed_value=speed_rpm, method="table", confidence=0.9)
        t_ref = EvidenceRef(source_id="s", source_type="pdf", product_id="T",
                            attribute="full_load_torque_nm", raw_value=str(torque_nm), raw_unit="Nm",
                            parsed_value=torque_nm, method="table", confidence=0.9)
        p_field = NormalizedField(canonical_field="rated_power", canonical_unit="kW",
                                  canonical_value=power_kw, outcome=NormalizationOutcome.PASSTHROUGH,
                                  evidence_refs=[p_ref])
        n_field = NormalizedField(canonical_field="rated_speed", canonical_unit="rpm",
                                  canonical_value=speed_rpm, outcome=NormalizationOutcome.PASSTHROUGH,
                                  evidence_refs=[n_ref])
        return NormalizedProduct(
            product_id="T", manufacturer="WEG", model="W22",
            fields={"rated_power": p_field, "rated_speed": n_field},
            unmapped_evidence=[t_ref],
        )

    def test_torque_power_rpm_passes_for_known_good_data(self):
        """1.1 kW, 1455 rpm → T_expected ≈ 7.22 Nm — should PASS."""
        from productiq.validation.rules import check_engineering_torque_power_rpm
        product = self._product_for_torque(1.1, 1455.0, 7.22)
        findings = check_engineering_torque_power_rpm(product)
        assert findings[0].status.value == "PASS"

    def test_torque_power_rpm_formula_result(self):
        """Verify the formula is correct: T = (P×1000×60)/(2π×N)."""
        p_kw = 1.1
        n_rpm = 1455.0
        t_expected = (p_kw * 1000.0 * 60.0) / (2.0 * math.pi * n_rpm)
        assert abs(t_expected - 7.219) < 0.01, f"Expected ~7.22 Nm, got {t_expected:.3f}"

    def test_torque_power_rpm_warns_for_bad_data(self):
        """Wildly wrong torque should produce WARNING."""
        from productiq.validation.rules import check_engineering_torque_power_rpm
        product = self._product_for_torque(1.1, 1455.0, 100.0)  # 100 Nm is way too high
        findings = check_engineering_torque_power_rpm(product)
        assert findings[0].status.value == "WARNING"

    def test_missing_torque_not_checked(self):
        """Missing torque in unmapped → NOT_CHECKED."""
        from productiq.validation.rules import check_engineering_torque_power_rpm
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        p_field = NormalizedField(canonical_field="rated_power", canonical_unit="kW",
                                  canonical_value=1.1, outcome=NormalizationOutcome.PASSTHROUGH)
        n_field = NormalizedField(canonical_field="rated_speed", canonical_unit="rpm",
                                  canonical_value=1455.0, outcome=NormalizationOutcome.PASSTHROUGH)
        product = NormalizedProduct(product_id="T", manufacturer="T", model="T",
                                    fields={"rated_power": p_field, "rated_speed": n_field},
                                    unmapped_evidence=[])
        findings = check_engineering_torque_power_rpm(product)
        assert findings[0].status.value == "NOT_CHECKED"

    def test_synchronous_speed_4_pole_50hz(self):
        """4-pole, 50 Hz → ns=1500 rpm. rated_speed=1455 rpm should PASS."""
        from productiq.validation.rules import check_engineering_synchronous_speed
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        n_field = NormalizedField(canonical_field="rated_speed", canonical_unit="rpm",
                                  canonical_value=1455.0, outcome=NormalizationOutcome.PASSTHROUGH)
        product = NormalizedProduct(product_id="PIQ-W22SP-4P-TEST", manufacturer="WEG",
                                    model="W22", fields={"rated_speed": n_field})
        findings = check_engineering_synchronous_speed(product)
        assert findings[0].status.value == "PASS"

    def test_synchronous_speed_fail_above_ns(self):
        """Speed above synchronous → FAIL."""
        from productiq.validation.rules import check_engineering_synchronous_speed
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        n_field = NormalizedField(canonical_field="rated_speed", canonical_unit="rpm",
                                  canonical_value=1600.0, outcome=NormalizationOutcome.PASSTHROUGH)
        product = NormalizedProduct(product_id="PIQ-W22SP-4P-TEST", manufacturer="WEG",
                                    model="W22", fields={"rated_speed": n_field})
        findings = check_engineering_synchronous_speed(product)
        assert findings[0].status.value == "FAIL"


# ---------------------------------------------------------------------------
# Provenance preservation through validation
# ---------------------------------------------------------------------------

class TestProvenancePreservation:
    @pytest.fixture(scope="class")
    def demo_report(self):
        path = PROCESSED_DIR / DEMO_PRODUCT_ID / "validation_report.json"
        if not path.exists():
            pytest.skip("validation_report.json not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_conflict_finding_has_evidence_refs(self, demo_report):
        conflict_findings = [f for f in demo_report["findings"] if f["status"] == "CONFLICT"]
        assert len(conflict_findings) > 0
        for f in conflict_findings:
            assert len(f["evidence_refs"]) >= 1, (
                f"Conflict finding {f['rule_id']} must have at least one evidence_ref."
            )

    def test_evidence_ref_has_source_type(self, demo_report):
        conflict_findings = [f for f in demo_report["findings"] if f["status"] == "CONFLICT"]
        for finding in conflict_findings:
            for ref in finding["evidence_refs"]:
                assert ref["source_type"] in ("pdf", "csv", "web"), (
                    f"evidence_ref must have valid source_type, got '{ref['source_type']}'"
                )

    def test_evidence_ref_has_raw_value(self, demo_report):
        conflict_findings = [f for f in demo_report["findings"] if f["status"] == "CONFLICT"]
        for finding in conflict_findings:
            for ref in finding["evidence_refs"]:
                assert ref["raw_value"] != "", (
                    "evidence_ref must preserve non-empty raw_value."
                )


# ---------------------------------------------------------------------------
# All 12 products: output existence and basic quality
# ---------------------------------------------------------------------------

class TestAllProductsValidated:
    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_validation_report_exists(self, product_id):
        path = PROCESSED_DIR / product_id / "validation_report.json"
        assert path.exists(), (
            f"validation_report.json not found for {product_id}. "
            "Run scripts/run_validation.py first."
        )

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_report_has_correct_product_id(self, product_id):
        path = PROCESSED_DIR / product_id / "validation_report.json"
        if not path.exists():
            pytest.skip(f"Missing report for {product_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["product_id"] == product_id

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_report_has_findings(self, product_id):
        path = PROCESSED_DIR / product_id / "validation_report.json"
        if not path.exists():
            pytest.skip(f"Missing report for {product_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["findings"]) > 0, f"No findings for {product_id}"

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_report_has_overall_status(self, product_id):
        path = PROCESSED_DIR / product_id / "validation_report.json"
        if not path.exists():
            pytest.skip(f"Missing report for {product_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["overall_status"] in ("PASS", "WARNING", "CONFLICT", "FAIL"), (
            f"Invalid overall_status for {product_id}: {data['overall_status']}"
        )

    def test_batch_report_exists(self):
        path = PROCESSED_DIR / "batch_validation_report.json"
        assert path.exists(), "batch_validation_report.json not found"

    def test_batch_report_processed_12(self):
        path = PROCESSED_DIR / "batch_validation_report.json"
        if not path.exists():
            pytest.skip("batch_validation_report.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["products_processed"] == 12


# ---------------------------------------------------------------------------
# No fabricated values
# ---------------------------------------------------------------------------

class TestNoFabricatedValues:
    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_no_conflict_finding_invents_winner(self, product_id):
        """Every CONFLICT finding must not override canonical_value in normalized product."""
        norm_path = PROCESSED_DIR / product_id / "normalized_product.json"
        val_path = PROCESSED_DIR / product_id / "validation_report.json"
        if not norm_path.exists() or not val_path.exists():
            pytest.skip(f"Missing files for {product_id}")

        norm_data = json.loads(norm_path.read_text(encoding="utf-8"))
        val_data = json.loads(val_path.read_text(encoding="utf-8"))

        # Find all CONFLICT findings and verify their fields still have no canonical_value
        for finding in val_data["findings"]:
            if finding["status"] == "CONFLICT":
                field_name = finding["field"]
                if field_name in norm_data["fields"]:
                    nf = norm_data["fields"][field_name]
                    assert nf["canonical_value"] is None, (
                        f"{product_id}.{field_name}: CONFLICT finding exists but "
                        f"normalized canonical_value is {nf['canonical_value']} — "
                        "validation must not invent a winner."
                    )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_validation_deterministic(self):
        from productiq.validation import MotorValidator
        from productiq.validation.validator import _load_normalized_product

        path = PROCESSED_DIR / DEMO_PRODUCT_ID / "normalized_product.json"
        if not path.exists():
            pytest.skip("normalized_product.json not found")

        product = _load_normalized_product(path)
        validator = MotorValidator()

        report_1 = validator.validate(product)
        report_2 = validator.validate(product)

        assert report_1.to_json() == report_2.to_json(), (
            "Validation must be deterministic: same input → same output"
        )
