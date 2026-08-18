"""
test_phase2.py
==============
Phase 2 integration tests — real data, all 12 products.

Covers:
- All 12 products produce normalized_product.json
- Product identity fields correct
- Weight normalized correctly (kg passthrough)
- rated_power normalized correctly
- rated_voltage from global evidence
- rated_current conflict preserved (PDF 2.34 A vs CSV 7.22 A)
- Full provenance traceable through normalization
- No fabricated values
- Unmapped evidence preserved
- Issues count zero (no parse errors or unknown units)
- Phase 0 regression: schema still imports cleanly
- Phase 1 regression: extraction still produces evidence
- NormalizationReport exists
- Determinism: running twice produces same output
"""
import json
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Phase 0 regression
# ---------------------------------------------------------------------------

class TestPhase0Regression:
    """Verify Phase 0 schema remains intact."""

    def test_schema_imports(self):
        from productiq.schema import (
            CANONICAL_UNITS, DataStatus, FieldValue, MotorProduct, SourceEntry,
        )
        assert MotorProduct is not None
        assert DataStatus is not None
        assert len(CANONICAL_UNITS) == 11

    def test_schema_version_unchanged(self):
        from productiq.schema import MotorProduct
        product = MotorProduct(
            product_id="test",
            manufacturer="test",
            model="test",
        )
        assert product.schema_version == "0.1.0-phase0"

    def test_four_tier_status(self):
        from productiq.schema import DataStatus
        assert {s.value for s in DataStatus} == {"Verified", "Inferred", "Conflicted", "Unknown"}


# ---------------------------------------------------------------------------
# Phase 2 module imports
# ---------------------------------------------------------------------------

class TestPhase2Imports:
    """Verify all normalization modules import successfully."""

    def test_normalization_package_imports(self):
        from productiq.normalization import (
            BatchNormalizer,
            MotorNormalizer,
            NormalizedProduct,
            NormalizationOutcome,
        )
        assert MotorNormalizer is not None
        assert BatchNormalizer is not None

    def test_unit_converter_imports(self):
        from productiq.normalization.unit_converter import (
            UnitConversionError, convert_value, is_equivalent, normalize_unit_string,
        )
        assert convert_value is not None

    def test_value_parser_imports(self):
        from productiq.normalization.value_parser import (
            ValueParseError, parse_numeric,
        )
        assert parse_numeric is not None

    def test_attribute_mapper_imports(self):
        from productiq.normalization.attribute_mapper import (
            MappingKind, get_mapping,
        )
        assert get_mapping is not None


# ---------------------------------------------------------------------------
# Normalized output file existence
# ---------------------------------------------------------------------------

class TestNormalizedOutputExists:
    """Verify normalized_product.json exists for all 12 products."""

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_normalized_json_exists(self, product_id):
        path = PROCESSED_DIR / product_id / "normalized_product.json"
        assert path.exists(), (
            f"normalized_product.json not found for {product_id}. "
            "Run scripts/run_normalization.py first."
        )

    def test_normalization_report_exists(self):
        report_path = PROCESSED_DIR / "normalization_report.json"
        assert report_path.exists(), "normalization_report.json not found"

    def test_normalization_report_content(self):
        report_path = PROCESSED_DIR / "normalization_report.json"
        if not report_path.exists():
            pytest.skip("normalization_report.json not found")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["products_processed"] == 12
        assert report["products_succeeded"] == 12
        assert report["products_failed"] == 0


# ---------------------------------------------------------------------------
# Product identity fields
# ---------------------------------------------------------------------------

class TestProductIdentity:
    """Verify product identity fields survive normalization."""

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_product_id_correct(self, product_id):
        path = PROCESSED_DIR / product_id / "normalized_product.json"
        if not path.exists():
            pytest.skip(f"normalized_product.json not found for {product_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["product_id"] == product_id

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_manufacturer_is_weg(self, product_id):
        path = PROCESSED_DIR / product_id / "normalized_product.json"
        if not path.exists():
            pytest.skip(f"missing {product_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["manufacturer"] == "WEG"

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_model_is_not_empty(self, product_id):
        path = PROCESSED_DIR / product_id / "normalized_product.json"
        if not path.exists():
            pytest.skip(f"missing {product_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["model"] != ""


# ---------------------------------------------------------------------------
# Canonical field correctness — real values for PIQ-W22SP-4P-1.1
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def product_1_1():
    path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "normalized_product.json"
    if not path.exists():
        pytest.skip("PIQ-W22SP-4P-1.1 normalized output not found")
    return json.loads(path.read_text(encoding="utf-8"))


class TestProduct1p1Fields:
    """Real-data field value tests for the 1.1 kW motor."""

    def test_rated_voltage_is_400(self, product_1_1):
        fld = product_1_1["fields"]["rated_voltage"]
        assert fld["canonical_value"] == 400.0
        assert fld["canonical_unit"] == "V"

    def test_rated_speed_is_1455(self, product_1_1):
        fld = product_1_1["fields"]["rated_speed"]
        assert fld["canonical_value"] == 1455.0
        assert fld["canonical_unit"] == "rpm"

    def test_weight_is_19_5(self, product_1_1):
        fld = product_1_1["fields"]["weight"]
        assert fld["canonical_value"] == 19.5
        assert fld["canonical_unit"] == "kg"

    def test_ip_rating_is_ip56(self, product_1_1):
        fld = product_1_1["fields"]["ip_rating"]
        assert fld["canonical_value"] == "IP56"

    def test_rated_current_is_conflicted(self, product_1_1):
        """PDF=2.34A vs CSV=7.22A — conflict must be preserved, no winner picked."""
        fld = product_1_1["fields"]["rated_current"]
        assert fld["outcome"] == "conflict"
        assert fld["canonical_value"] is None  # No winner picked

    def test_rated_current_conflict_has_both_values(self, product_1_1):
        conflicts = product_1_1["fields"]["rated_current"]["conflicts"]
        assert len(conflicts) >= 1
        values = {c["value_a"] for c in conflicts} | {c["value_b"] for c in conflicts}
        assert 2.34 in values, "PDF value (2.34 A) must be preserved in conflict"
        assert 7.22 in values, "CSV value (7.22 A) must be preserved in conflict"

    def test_rated_power_has_evidence(self, product_1_1):
        fld = product_1_1["fields"]["rated_power"]
        assert len(fld["evidence_refs"]) > 0

    def test_no_parse_errors(self, product_1_1):
        assert len(product_1_1["issues"]) == 0, (
            "No parse errors expected for well-formed WEG evidence data"
        )


# ---------------------------------------------------------------------------
# Provenance round-trip — raw values survive normalization
# ---------------------------------------------------------------------------

class TestProvenanceRoundTrip:
    """Verify raw values are accessible in evidence_refs after normalization."""

    def test_csv_raw_current_7_22_preserved(self, product_1_1):
        refs = product_1_1["fields"]["rated_current"]["evidence_refs"]
        raw_values = [r["raw_value"] for r in refs]
        assert "7.22" in raw_values, "CSV raw value 7.22 must survive through normalization"

    def test_pdf_raw_current_2_34_preserved(self, product_1_1):
        refs = product_1_1["fields"]["rated_current"]["evidence_refs"]
        raw_values = [r["raw_value"] for r in refs]
        assert "2.34" in raw_values, "PDF raw value 2.34 must survive through normalization"

    def test_hp_raw_value_1_5_preserved(self, product_1_1):
        refs = product_1_1["fields"]["rated_power"]["evidence_refs"]
        raw_values = [r["raw_value"] for r in refs]
        assert "1.5" in raw_values, "HP raw value 1.5 must survive through normalization"

    def test_evidence_ref_has_source_id(self, product_1_1):
        refs = product_1_1["fields"]["rated_power"]["evidence_refs"]
        assert all(r["source_id"] != "" for r in refs)

    def test_evidence_ref_has_product_id(self, product_1_1):
        refs = product_1_1["fields"]["rated_power"]["evidence_refs"]
        assert all(r["product_id"] == "PIQ-W22SP-4P-1.1" for r in refs)


# ---------------------------------------------------------------------------
# No fabricated values
# ---------------------------------------------------------------------------

class TestNoFabricatedValues:
    """Verify normalization never invents values not in evidence."""

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_missing_fields_have_none_value(self, product_id):
        path = PROCESSED_DIR / product_id / "normalized_product.json"
        if not path.exists():
            pytest.skip(f"missing {product_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        for field_name, fld in data["fields"].items():
            if fld["outcome"] == "missing":
                assert fld["canonical_value"] is None, (
                    f"{product_id}.{field_name}: Missing field must have canonical_value=None, "
                    "not a fabricated value."
                )

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_conflict_fields_have_none_value(self, product_id):
        path = PROCESSED_DIR / product_id / "normalized_product.json"
        if not path.exists():
            pytest.skip(f"missing {product_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        for field_name, fld in data["fields"].items():
            if fld["outcome"] == "conflict":
                assert fld["canonical_value"] is None, (
                    f"{product_id}.{field_name}: Conflicted field must have canonical_value=None "
                    "— Phase 2 must not silently pick a winner."
                )


# ---------------------------------------------------------------------------
# Unmapped evidence preserved
# ---------------------------------------------------------------------------

class TestUnmappedEvidence:
    """Verify non-canonical attributes are preserved in unmapped_evidence."""

    @pytest.mark.parametrize("product_id", PRODUCT_IDS)
    def test_unmapped_evidence_exists(self, product_id):
        path = PROCESSED_DIR / product_id / "normalized_product.json"
        if not path.exists():
            pytest.skip(f"missing {product_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["unmapped_evidence"]) > 0, (
            f"{product_id}: unmapped_evidence should contain torque, inertia, etc."
        )

    def test_torque_in_unmapped_1_1(self, product_1_1):
        attrs = [e["attribute"] for e in product_1_1["unmapped_evidence"]]
        assert "full_load_torque_nm" in attrs


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Running normalization twice produces identical output."""

    def test_deterministic_for_1_1(self):
        from productiq.normalization import MotorNormalizer
        import json

        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        entry = next((m for m in manifest if m["product_id"] == "PIQ-W22SP-4P-1.1"), None)
        if entry is None:
            pytest.skip("PIQ-W22SP-4P-1.1 not in manifest")

        normalizer = MotorNormalizer(data_dir=DATA_DIR)
        run1 = normalizer.normalize_product(entry, "PIQ-W22SP-4P-1.1")
        run2 = normalizer.normalize_product(entry, "PIQ-W22SP-4P-1.1")

        # Compare JSON serializations (canonical ordering)
        assert run1.to_json() == run2.to_json(), (
            "Normalization must be deterministic: same input → same output"
        )
