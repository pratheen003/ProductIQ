"""
ProductIQ Phase 2 Verification Script
=======================================
Automated audit of the Phase 2 normalization layer.

Runs 13 verification checks and reports results.

Usage:
    python scripts/verify_phase2.py

Exit code: 0 (all pass) or 1 (any fail).
"""
import json
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR      = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFEST_PATH = DATA_DIR / "dataset_manifest.json"
DOCS_DIR      = PROJECT_ROOT / "docs"

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
# Check runner
# ---------------------------------------------------------------------------

class CheckRunner:
    def __init__(self):
        self.results = []

    def check(self, label: str, fn):
        try:
            fn()
            self.results.append((True, label, None))
            print(f"  [PASS] {label}")
        except AssertionError as e:
            self.results.append((False, label, str(e)))
            print(f"  [FAIL] {label}: {e}")
        except Exception as e:
            self.results.append((False, label, f"{type(e).__name__}: {e}"))
            print(f"  [FAIL] {label}: {type(e).__name__}: {e}")

    @property
    def all_passed(self):
        return all(ok for ok, _, _ in self.results)

    @property
    def pass_count(self):
        return sum(1 for ok, _, _ in self.results if ok)

    @property
    def total_count(self):
        return len(self.results)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_phase0_baseline():
    """Phase 0 baseline: schema, enum, canonical units."""
    from productiq.schema import CANONICAL_UNITS, DataStatus, FieldValue, MotorProduct, SourceEntry
    assert len(CANONICAL_UNITS) == 11, f"Expected 11 canonical units, got {len(CANONICAL_UNITS)}"
    assert set(s.value for s in DataStatus) == {"Verified", "Inferred", "Conflicted", "Unknown"}
    p = MotorProduct(product_id="verify-test", manufacturer="Test", model="Test")
    assert p.schema_version == "0.1.0-phase0"


def check_phase1_baseline():
    """Phase 1 baseline: extraction modules import and evidence exists."""
    from productiq.extraction import (
        CSVExtractor, EvidenceRecord, ExtractionResult, PDFExtractor, WebExtractor,
    )
    assert PDFExtractor is not None
    assert CSVExtractor is not None
    # Verify at least one product has evidence
    pdf_path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "pdf_evidence.json"
    assert pdf_path.exists(), "PDF evidence for PIQ-W22SP-4P-1.1 not found"
    data = json.loads(pdf_path.read_text(encoding="utf-8"))
    assert len(data.get("evidence", [])) > 0


def check_normalization_modules_import():
    """Normalization modules, models, and main normalizer import successfully."""
    from productiq.normalization import (
        BatchNormalizer,
        MotorNormalizer,
        NormalizationOutcome,
        NormalizedField,
        NormalizedProduct,
    )
    from productiq.normalization.attribute_mapper import get_mapping
    from productiq.normalization.unit_converter import convert_value
    from productiq.normalization.value_parser import parse_numeric
    assert MotorNormalizer is not None


def check_normalization_models_serialize():
    """NormalizedProduct and NormalizedField can be serialized and round-tripped."""
    from productiq.normalization.models import (
        EvidenceRef, NormalizationOutcome, NormalizedField, NormalizedProduct,
    )

    ref = EvidenceRef(
        source_id="test", source_type="pdf", product_id="TEST-001",
        attribute="rated_power", raw_value="1.1", raw_unit="kW",
        parsed_value=1.1, method="table", confidence=0.92, page=5,
    )
    fld = NormalizedField(
        canonical_field="rated_power",
        canonical_unit="kW",
        canonical_value=1.1,
        outcome=NormalizationOutcome.PASSTHROUGH,
        evidence_refs=[ref],
    )
    prod = NormalizedProduct(
        product_id="TEST-001", manufacturer="Test", model="Test Model",
        fields={"rated_power": fld},
    )
    json_str = prod.to_json()
    data = json.loads(json_str)
    assert data["product_id"] == "TEST-001"
    assert data["fields"]["rated_power"]["canonical_value"] == 1.1


def check_canonical_unit_conversion():
    """Canonical unit conversion is correct and deterministic."""
    from productiq.normalization.unit_converter import convert_value

    # 1100 W → 1.1 kW
    val, unit = convert_value("rated_power", 1100.0, "W")
    assert unit == "kW", f"Expected kW, got {unit}"
    assert abs(val - 1.1) < 1e-6, f"Expected 1.1 kW, got {val}"

    # 1.5 HP → 1.11855 kW
    val2, unit2 = convert_value("rated_power", 1.5, "HP")
    assert unit2 == "kW"
    assert abs(val2 - 1.11855) < 1e-4, f"Expected ~1.11855 kW, got {val2}"

    # 19500 g → 19.5 kg
    val3, unit3 = convert_value("weight", 19500.0, "g")
    assert unit3 == "kg"
    assert abs(val3 - 19.5) < 1e-6

    # Determinism
    v1, _ = convert_value("rated_power", 1100.0, "W")
    v2, _ = convert_value("rated_power", 1100.0, "W")
    assert v1 == v2


def check_attribute_mapping():
    """Attribute mapping correctly classifies evidence attributes."""
    from productiq.normalization.attribute_mapper import MappingKind, get_mapping

    # Canonical mappings
    field, kind, _ = get_mapping("rated_power_hp")
    assert field == "rated_power" and kind == MappingKind.CANONICAL

    field2, kind2, _ = get_mapping("full_load_current_a")
    assert field2 == "rated_current" and kind2 == MappingKind.CANONICAL

    # Unmapped
    _, kind3, _ = get_mapping("full_load_torque_nm")
    assert kind3 == MappingKind.UNMAPPED

    # Metadata
    _, kind4, _ = get_mapping("rated_power_unit")
    assert kind4 == MappingKind.METADATA

    # All canonical fields reachable
    from productiq.normalization.attribute_mapper import _ATTRIBUTE_MAP
    from productiq.schema import CANONICAL_UNITS
    for cfield in CANONICAL_UNITS:
        reachable = any(
            cf == cfield and k == MappingKind.CANONICAL
            for cf, k, _ in _ATTRIBUTE_MAP.values()
        )
        assert reachable, f"Canonical field '{cfield}' is not reachable from any attribute mapping"


def check_provenance_survives_normalization():
    """Raw values and source provenance survive through normalization."""
    path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "normalized_product.json"
    assert path.exists(), "normalized_product.json not found for PIQ-W22SP-4P-1.1"
    data = json.loads(path.read_text(encoding="utf-8"))

    # Check rated_current evidence_refs contains both PDF and CSV raw values
    rc_refs = data["fields"]["rated_current"]["evidence_refs"]
    raw_values = {r["raw_value"] for r in rc_refs}
    assert "2.34" in raw_values, f"PDF raw value 2.34 A not found in evidence_refs. Got: {raw_values}"
    assert "7.22" in raw_values, f"CSV raw value 7.22 A not found in evidence_refs. Got: {raw_values}"

    # Check source_id preserved
    assert all(r["source_id"] != "" for r in rc_refs), "source_id must not be empty"

    # Check product_id preserved
    assert all(r["product_id"] == "PIQ-W22SP-4P-1.1" for r in rc_refs)


def check_conflicting_evidence_preserved():
    """Conflicting evidence is preserved, no silent winner picked."""
    path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "normalized_product.json"
    if not path.exists():
        raise AssertionError("normalized_product.json not found")
    data = json.loads(path.read_text(encoding="utf-8"))

    rc = data["fields"]["rated_current"]
    assert rc["outcome"] == "conflict", (
        f"rated_current should be conflicted (PDF 2.34A vs CSV 7.22A), "
        f"got outcome='{rc['outcome']}'"
    )
    assert rc["canonical_value"] is None, (
        "Conflicted field must have canonical_value=None — no winner picked"
    )
    conflicts = rc["conflicts"]
    assert len(conflicts) >= 1, "At least one conflict record expected"

    all_conflict_values = set()
    for c in conflicts:
        if c.get("value_a") is not None:
            all_conflict_values.add(c["value_a"])
        if c.get("value_b") is not None:
            all_conflict_values.add(c["value_b"])
    assert 2.34 in all_conflict_values, "PDF value 2.34 must be in conflicts"
    assert 7.22 in all_conflict_values, "CSV value 7.22 must be in conflicts"


def check_missing_values_handled_safely():
    """Missing evidence fields are represented as Missing, never guessed."""
    path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "normalized_product.json"
    if not path.exists():
        raise AssertionError("normalized_product.json not found")
    data = json.loads(path.read_text(encoding="utf-8"))

    for field_name, fld in data["fields"].items():
        if fld["outcome"] == "missing":
            assert fld["canonical_value"] is None, (
                f"{field_name}: Missing field has non-None canonical_value — "
                "normalization must never fabricate missing values."
            )


def check_all_12_products_normalize():
    """All 12 products in the manifest produce normalized output."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert len(manifest) == 12, f"Expected 12 products in manifest, got {len(manifest)}"

    for entry in manifest:
        pid = entry["product_id"]
        out_path = PROCESSED_DIR / pid / "normalized_product.json"
        assert out_path.exists(), f"normalized_product.json not found for {pid}"
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["product_id"] == pid
        assert "fields" in data
        assert len(data["fields"]) == 11  # 11 canonical fields from Phase 0


def check_normalized_output_exists():
    """Normalized output files and batch report exist."""
    for pid in PRODUCT_IDS:
        path = PROCESSED_DIR / pid / "normalized_product.json"
        assert path.exists(), f"Missing: {path}"

    report_path = PROCESSED_DIR / "normalization_report.json"
    assert report_path.exists(), "normalization_report.json not found"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["products_processed"] == 12
    assert report["products_succeeded"] == 12
    assert report["products_failed"] == 0


def check_no_fabricated_values():
    """Verify no field contains an invented value — all values trace to evidence."""
    for pid in PRODUCT_IDS:
        path = PROCESSED_DIR / pid / "normalized_product.json"
        if not path.exists():
            raise AssertionError(f"Missing output for {pid}")
        data = json.loads(path.read_text(encoding="utf-8"))

        for field_name, fld in data["fields"].items():
            # If the field has a value, it must have at least one evidence_ref
            if fld["canonical_value"] is not None:
                refs = fld.get("evidence_refs", [])
                assert len(refs) > 0, (
                    f"{pid}.{field_name}: canonical_value={fld['canonical_value']} "
                    "but evidence_refs is empty — this would be a fabricated value."
                )
            # Conflict fields must not have a value
            if fld["outcome"] == "conflict":
                assert fld["canonical_value"] is None, (
                    f"{pid}.{field_name}: conflict outcome but canonical_value is not None"
                )


def check_documentation_exists():
    """Phase 2 documentation files exist."""
    required_docs = [
        DOCS_DIR / "PHASE_2.md",
        DOCS_DIR / "NORMALIZATION.md",
        PROJECT_ROOT / "walkthrough.md",
    ]
    for doc_path in required_docs:
        assert doc_path.exists(), f"Documentation file missing: {doc_path}"
        content = doc_path.read_text(encoding="utf-8").strip()
        assert len(content) > 100, f"{doc_path.name} appears to be empty or too short"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print()
    print("=" * 60)
    print("  ProductIQ Phase 2 Verification")
    print("=" * 60)
    print()

    runner = CheckRunner()

    runner.check("Phase 0 baseline intact (schema, enum, canonical units)",
                 check_phase0_baseline)
    runner.check("Phase 1 baseline intact (extraction modules, evidence exists)",
                 check_phase1_baseline)
    runner.check("Normalization modules import successfully",
                 check_normalization_modules_import)
    runner.check("Normalization models serialize and round-trip",
                 check_normalization_models_serialize)
    runner.check("Canonical unit conversion correct and deterministic",
                 check_canonical_unit_conversion)
    runner.check("Attribute mapping correct (canonical / unmapped / metadata)",
                 check_attribute_mapping)
    runner.check("Provenance survives normalization (raw values traceable)",
                 check_provenance_survives_normalization)
    runner.check("Conflicting evidence preserved, no silent winner picked",
                 check_conflicting_evidence_preserved)
    runner.check("Missing values handled safely (Unknown, not guessed)",
                 check_missing_values_handled_safely)
    runner.check("All 12 products normalize successfully",
                 check_all_12_products_normalize)
    runner.check("Normalized output files exist (all 12 + batch report)",
                 check_normalized_output_exists)
    runner.check("No fabricated values (all values trace to evidence)",
                 check_no_fabricated_values)
    runner.check("Documentation complete (PHASE_2.md, NORMALIZATION.md, walkthrough.md)",
                 check_documentation_exists)

    print()
    print("=" * 60)
    if runner.all_passed:
        print(f"  PHASE 2 STATUS: COMPLETE [OK]")
        print(f"  All {runner.total_count} checks passed.")
    else:
        failed = runner.total_count - runner.pass_count
        print(f"  PHASE 2 STATUS: INCOMPLETE [{runner.pass_count}/{runner.total_count} passed, {failed} failed]")
    print("=" * 60)
    print()

    return 0 if runner.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
