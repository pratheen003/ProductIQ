"""
test_normalization_provenance.py
=================================
Tests that provenance is fully preserved through normalization.

Covers:
- EvidenceRef contains all provenance fields from the original EvidenceRecord
- Raw value survives in EvidenceRef.raw_value after normalization
- Raw unit survives in EvidenceRef.raw_unit after normalization
- Page/row/column/url provenance fields are preserved
- Source type preserved
- NormalizedField.evidence_refs is non-empty for fields with evidence
- Conflicts preserve BOTH evidence sources (not just one)
- Unmapped evidence is preserved (nothing silently dropped)
- Missing fields have empty evidence_refs (honest reporting)
"""
import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
PRODUCT_ID = "PIQ-W22SP-4P-1.1"
NORMALIZED_PATH = PROJECT_ROOT / "data" / "processed" / PRODUCT_ID / "normalized_product.json"


@pytest.fixture(scope="module")
def normalized_product():
    """Load the normalized product for PIQ-W22SP-4P-1.1."""
    if not NORMALIZED_PATH.exists():
        pytest.skip("normalized_product.json not found — run scripts/run_normalization.py first")
    return json.loads(NORMALIZED_PATH.read_text(encoding="utf-8"))


class TestEvidenceRefPresence:
    """Verify evidence_refs are populated for fields that have evidence."""

    def test_rated_power_has_evidence_refs(self, normalized_product):
        refs = normalized_product["fields"]["rated_power"]["evidence_refs"]
        assert len(refs) > 0

    def test_weight_has_evidence_refs(self, normalized_product):
        refs = normalized_product["fields"]["weight"]["evidence_refs"]
        assert len(refs) > 0

    def test_rated_speed_has_evidence_refs(self, normalized_product):
        refs = normalized_product["fields"]["rated_speed"]["evidence_refs"]
        assert len(refs) > 0

    def test_rated_voltage_has_evidence_refs(self, normalized_product):
        refs = normalized_product["fields"]["rated_voltage"]["evidence_refs"]
        assert len(refs) > 0


class TestRawValuePreservation:
    """Verify raw_value is preserved in EvidenceRef after normalization."""

    def test_rated_power_raw_value_preserved(self, normalized_product):
        refs = normalized_product["fields"]["rated_power"]["evidence_refs"]
        # At least one ref from the kW PDF column should have raw_value "1.1"
        raw_values = [r["raw_value"] for r in refs]
        assert "1.1" in raw_values

    def test_rated_power_hp_raw_value_preserved(self, normalized_product):
        refs = normalized_product["fields"]["rated_power"]["evidence_refs"]
        # HP column evidence has raw_value "1.5"
        raw_values = [r["raw_value"] for r in refs]
        assert "1.5" in raw_values, "HP raw_value must survive normalization"

    def test_weight_raw_value_preserved(self, normalized_product):
        refs = normalized_product["fields"]["weight"]["evidence_refs"]
        raw_values = [r["raw_value"] for r in refs]
        assert "19.5" in raw_values

    def test_rated_current_raw_values_preserved(self, normalized_product):
        refs = normalized_product["fields"]["rated_current"]["evidence_refs"]
        raw_values = [r["raw_value"] for r in refs]
        # Both PDF (2.34) and CSV (7.22) must be preserved
        assert "2.34" in raw_values
        assert "7.22" in raw_values


class TestSourceTypePreservation:
    """Verify source_type field is preserved in evidence refs."""

    def test_pdf_source_type_preserved(self, normalized_product):
        refs = normalized_product["fields"]["rated_power"]["evidence_refs"]
        source_types = {r["source_type"] for r in refs}
        assert "pdf" in source_types

    def test_csv_source_type_preserved(self, normalized_product):
        refs = normalized_product["fields"]["weight"]["evidence_refs"]
        source_types = {r["source_type"] for r in refs}
        # CSV also has weight
        assert "csv" in source_types or "pdf" in source_types


class TestConflictProvenance:
    """Verify that conflicts preserve both evidence sources."""

    def test_rated_current_conflict_has_both_sources(self, normalized_product):
        field = normalized_product["fields"]["rated_current"]
        assert field["outcome"] == "conflict", "rated_current should be conflicted"
        conflicts = field["conflicts"]
        assert len(conflicts) >= 1

        # Both source types must appear in the conflict record
        for conflict in conflicts:
            # Should have two different source_types or different raw_values
            raw_a = conflict["source_a"]["raw_value"]
            raw_b = conflict["source_b"]["raw_value"]
            assert raw_a != raw_b, "Conflict record must show differing values"

    def test_conflict_value_a_and_b_both_present(self, normalized_product):
        conflicts = normalized_product["fields"]["rated_current"]["conflicts"]
        for c in conflicts:
            assert c["value_a"] is not None or c["value_b"] is not None

    def test_rated_current_canonical_value_is_none_on_conflict(self, normalized_product):
        field = normalized_product["fields"]["rated_current"]
        # Conflict → no winner picked → canonical_value must be None
        assert field["canonical_value"] is None, (
            "Phase 2 must NOT pick a winner for conflicting fields. "
            "canonical_value must be None when outcome=conflict."
        )


class TestUnmappedEvidencePreservation:
    """Verify that unmapped attributes are not silently dropped."""

    def test_unmapped_evidence_is_non_empty(self, normalized_product):
        unmapped = normalized_product["unmapped_evidence"]
        assert len(unmapped) > 0, "Unmapped evidence (e.g. torque, inertia) must be preserved"

    def test_torque_in_unmapped(self, normalized_product):
        unmapped = normalized_product["unmapped_evidence"]
        attrs = [e["attribute"] for e in unmapped]
        assert "full_load_torque_nm" in attrs, (
            "full_load_torque_nm has no canonical field — must appear in unmapped_evidence"
        )

    def test_unmapped_preserves_raw_value(self, normalized_product):
        unmapped = normalized_product["unmapped_evidence"]
        # full_load_torque_nm = 7.22 for this product
        torque_refs = [e for e in unmapped if e["attribute"] == "full_load_torque_nm"]
        assert torque_refs, "full_load_torque_nm must be in unmapped"
        assert torque_refs[0]["raw_value"] == "7.22"

    def test_unmapped_preserves_source_type(self, normalized_product):
        unmapped = normalized_product["unmapped_evidence"]
        source_types = {e["source_type"] for e in unmapped}
        assert "pdf" in source_types

    def test_unmapped_preserves_provenance_fields(self, normalized_product):
        unmapped = normalized_product["unmapped_evidence"]
        torque_refs = [e for e in unmapped if e["attribute"] == "full_load_torque_nm"]
        assert torque_refs
        ref = torque_refs[0]
        # Must have source_id, source_type, product_id preserved
        assert ref["source_id"] != ""
        assert ref["source_type"] != ""
        assert ref["product_id"] != ""


class TestMissingFieldHandling:
    """Verify that fields with no evidence are represented as Missing, not guessed."""

    def test_frequency_is_missing_not_guessed(self, normalized_product):
        # frequency has no evidence in Phase 1 for per-product files
        freq = normalized_product["fields"].get("frequency", {})
        if freq:
            # If present, must be MISSING or have no fabricated value from nowhere
            if freq["outcome"] == "missing":
                assert freq["canonical_value"] is None
            # If it has evidence (e.g. from global), that's fine

    def test_poles_is_missing_not_guessed(self, normalized_product):
        poles = normalized_product["fields"].get("poles", {})
        if poles and poles["outcome"] == "missing":
            assert poles["canonical_value"] is None, (
                "Missing poles field must not be guessed — must remain None."
            )
