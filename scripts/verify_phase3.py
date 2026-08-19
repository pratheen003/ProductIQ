"""
ProductIQ Phase 3 Verification Script
=======================================
16-point automated audit of the Phase 3 validation engine.

Usage:
    python scripts/verify_phase3.py

Expected result:
    PHASE 3 STATUS: COMPLETE [OK]
    All 16 checks passed.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFEST_PATH = DATA_DIR / "dataset_manifest.json"

sys.path.insert(0, str(PROJECT_ROOT))

PASS = "[PASS]"
FAIL = "[FAIL]"


def _check(label: str, fn) -> bool:
    try:
        fn()
        print(f"  {PASS} {label}")
        return True
    except Exception as exc:
        print(f"  {FAIL} {label}")
        print(f"         └─ {exc}")
        return False


def run_checks() -> int:
    print()
    print("=" * 60)
    print("  ProductIQ Phase 3 Verification")
    print("=" * 60)
    print()

    results = []

    # -----------------------------------------------------------------------
    # 1. Phase 0 baseline intact
    # -----------------------------------------------------------------------
    def check_phase0():
        from productiq.schema import CANONICAL_UNITS, DataStatus, MotorProduct
        assert len(CANONICAL_UNITS) == 11
        assert {s.value for s in DataStatus} == {"Verified", "Inferred", "Conflicted", "Unknown"}
        p = MotorProduct(product_id="t", manufacturer="t", model="t")
        assert p.schema_version == "0.1.0-phase0"

    results.append(_check("Phase 0 baseline intact (schema, enum, canonical units)", check_phase0))

    # -----------------------------------------------------------------------
    # 2. Phase 1 baseline intact
    # -----------------------------------------------------------------------
    def check_phase1():
        from productiq.extraction.models import EvidenceRecord, ExtractionResult
        from productiq.extraction.pdf_extractor import PDFExtractor
        from productiq.extraction.csv_extractor import CSVExtractor
        assert EvidenceRecord is not None
        assert PDFExtractor is not None
        assert CSVExtractor is not None

    results.append(_check("Phase 1 baseline intact (extraction modules and models)", check_phase1))

    # -----------------------------------------------------------------------
    # 3. Phase 2 baseline intact
    # -----------------------------------------------------------------------
    def check_phase2():
        from productiq.normalization import MotorNormalizer, NormalizedProduct
        assert MotorNormalizer is not None
        norm_path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "normalized_product.json"
        assert norm_path.exists(), f"normalized_product.json missing: {norm_path}"
        data = json.loads(norm_path.read_text(encoding="utf-8"))
        assert "fields" in data
        assert data["product_id"] == "PIQ-W22SP-4P-1.1"

    results.append(_check("Phase 2 baseline intact (normalization output exists)", check_phase2))

    # -----------------------------------------------------------------------
    # 4. Validation modules import successfully
    # -----------------------------------------------------------------------
    def check_imports():
        from productiq.validation import (
            MotorValidator, BatchValidator,
            ProductValidationReport, ValidationFinding,
            ValidationStatus, ValidationSeverity, ValidationCategory,
        )
        from productiq.validation.models import BatchValidationReport, FindingEvidenceRef
        from productiq.validation.rules import (
            check_schema_canonical_units,
            check_required_fields,
            check_range_rated_power,
            check_cross_source_consistency,
            check_engineering_torque_power_rpm,
            check_known_current_conflict,
        )
        from productiq.validation.validator import _load_normalized_product
        assert MotorValidator is not None

    results.append(_check("Validation modules import successfully", check_imports))

    # -----------------------------------------------------------------------
    # 5. Validation models serialize and round-trip
    # -----------------------------------------------------------------------
    def check_models():
        from productiq.validation.models import (
            ValidationFinding, ValidationStatus, ValidationSeverity,
            ValidationCategory, ProductValidationReport,
        )
        f = ValidationFinding(
            rule_id="TEST", category=ValidationCategory.RANGE,
            status=ValidationStatus.PASS, severity=ValidationSeverity.INFO,
            field="rated_power", description="Test",
            explanation="Test explanation.",
        )
        d = f.to_dict()
        assert d["rule_id"] == "TEST"
        assert d["status"] == "PASS"

        report = ProductValidationReport(product_id="T", manufacturer="T", model="T")
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["product_id"] == "T"
        assert "findings" in data

    results.append(_check("Validation models serialize and round-trip (JSON)", check_models))

    # -----------------------------------------------------------------------
    # 6. Schema validation works
    # -----------------------------------------------------------------------
    def check_schema_validation():
        from productiq.validation.rules import check_schema_canonical_units
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        # Field with correct unit → PASS
        nf = NormalizedField(canonical_field="rated_power", canonical_unit="kW",
                             canonical_value=1.1, outcome=NormalizationOutcome.PASSTHROUGH)
        product = NormalizedProduct(product_id="T", manufacturer="T", model="T",
                                    fields={"rated_power": nf})
        findings = check_schema_canonical_units(product)
        assert any(f.status.value == "PASS" for f in findings), "Expected PASS for correct unit"
        # Field with wrong unit → FAIL
        nf_bad = NormalizedField(canonical_field="rated_power", canonical_unit="W",
                                 canonical_value=1100.0, outcome=NormalizationOutcome.PASSTHROUGH)
        product_bad = NormalizedProduct(product_id="T", manufacturer="T", model="T",
                                        fields={"rated_power": nf_bad})
        findings_bad = check_schema_canonical_units(product_bad)
        assert any(f.status.value == "FAIL" for f in findings_bad), "Expected FAIL for wrong unit"

    results.append(_check("Schema validation works (unit checks)", check_schema_validation))

    # -----------------------------------------------------------------------
    # 7. Required-field checks work
    # -----------------------------------------------------------------------
    def check_required_field_rules():
        from productiq.validation.rules import check_required_fields
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        from productiq.schema import CANONICAL_UNITS
        # Product with all fields missing → 3 FAILs
        fields = {
            fname: NormalizedField(
                canonical_field=fname,
                canonical_unit=CANONICAL_UNITS.get(fname),
                canonical_value=None,
                outcome=NormalizationOutcome.MISSING,
            )
            for fname in CANONICAL_UNITS
        }
        product = NormalizedProduct(product_id="E", manufacturer="T", model="T", fields=fields)
        findings = check_required_fields(product)
        fails = [f for f in findings if f.status.value == "FAIL"]
        assert len(fails) == 3, f"Expected 3 FAIL findings, got {len(fails)}"

    results.append(_check("Required-field checks work (missing required -> FAIL)", check_required_field_rules))

    # -----------------------------------------------------------------------
    # 8. Range rules work
    # -----------------------------------------------------------------------
    def check_range_rules():
        from productiq.validation.rules import check_range_rated_power, check_range_efficiency
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome

        def make_p(field, val, unit=None):
            nf = NormalizedField(canonical_field=field, canonical_unit=unit,
                                 canonical_value=val, outcome=NormalizationOutcome.PASSTHROUGH)
            return NormalizedProduct(product_id="T", manufacturer="T", model="T",
                                     fields={field: nf})

        # Power > 0 passes
        assert check_range_rated_power(make_p("rated_power", 1.1, "kW"))[0].status.value == "PASS"
        # Power = 0 fails
        assert check_range_rated_power(make_p("rated_power", 0.0, "kW"))[0].status.value == "FAIL"
        # Efficiency 101% fails
        assert check_range_efficiency(make_p("efficiency", 101.0, "%"))[0].status.value == "FAIL"
        # Efficiency -1% fails
        assert check_range_efficiency(make_p("efficiency", -1.0, "%"))[0].status.value == "FAIL"
        # Efficiency 84.8% passes
        assert check_range_efficiency(make_p("efficiency", 84.8, "%"))[0].status.value == "PASS"

    results.append(_check("Range rules work (valid/invalid value detection)", check_range_rules))

    # -----------------------------------------------------------------------
    # 9. Cross-source consistency works
    # -----------------------------------------------------------------------
    def check_cross_source():
        from productiq.validation.rules import check_cross_source_consistency
        from productiq.normalization.models import (
            NormalizedProduct, NormalizedField, NormalizationOutcome,
            ConflictRecord, EvidenceRef,
        )
        ref_a = EvidenceRef(source_id="s", source_type="pdf", product_id="T",
                            attribute="rated_current", raw_value="2.34", raw_unit="A",
                            parsed_value=2.34, method="table", confidence=0.9)
        ref_b = EvidenceRef(source_id="s", source_type="csv", product_id="T",
                            attribute="rated_current", raw_value="7.22", raw_unit="A",
                            parsed_value=7.22, method="column", confidence=0.85)
        conflict = ConflictRecord(canonical_field="rated_current",
                                  value_a=2.34, unit_a="A", source_a=ref_a,
                                  value_b=7.22, unit_b="A", source_b=ref_b)
        nf = NormalizedField(canonical_field="rated_current", canonical_unit="A",
                             canonical_value=None, outcome=NormalizationOutcome.CONFLICT,
                             evidence_refs=[ref_a, ref_b], conflicts=[conflict])
        product = NormalizedProduct(product_id="T", manufacturer="T", model="T",
                                    fields={"rated_current": nf})
        findings = check_cross_source_consistency(product)
        assert len(findings) == 1
        assert findings[0].status.value == "CONFLICT"
        assert "2.34" in findings[0].explanation
        assert "7.22" in findings[0].explanation

    results.append(_check("Cross-source consistency works (conflict detected)", check_cross_source))

    # -----------------------------------------------------------------------
    # 10. Known real conflict (2.34 A vs 7.22 A) is explicitly detected
    # -----------------------------------------------------------------------
    def check_known_conflict():
        report_path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "validation_report.json"
        assert report_path.exists(), f"validation_report.json not found: {report_path}"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rule_ids = [f["rule_id"] for f in report["findings"]]
        assert "CONFLICT_RATED_CURRENT_PDF_VS_CSV" in rule_ids, (
            "HARD GATE: CONFLICT_RATED_CURRENT_PDF_VS_CSV not found in findings. "
            "The known 2.34 A (PDF) vs 7.22 A (CSV) conflict was not detected."
        )
        conflict_finding = next(
            f for f in report["findings"]
            if f["rule_id"] == "CONFLICT_RATED_CURRENT_PDF_VS_CSV"
        )
        assert conflict_finding["status"] == "CONFLICT"
        assert "2.34" in conflict_finding["explanation"]
        assert "7.22" in conflict_finding["explanation"]
        assert len(conflict_finding["evidence_refs"]) >= 2

    results.append(_check("Known real conflict detected (PDF 2.34 A vs CSV 7.22 A)", check_known_conflict))

    # -----------------------------------------------------------------------
    # 11. Engineering plausibility check works
    # -----------------------------------------------------------------------
    def check_engineering():
        import math
        from productiq.validation.rules import check_engineering_torque_power_rpm, check_engineering_synchronous_speed
        from productiq.normalization.models import (
            NormalizedProduct, NormalizedField, NormalizationOutcome, EvidenceRef,
        )

        def ev(attr, val, unit):
            return EvidenceRef(source_id="s", source_type="pdf", product_id="T",
                               attribute=attr, raw_value=str(val), raw_unit=unit,
                               parsed_value=val, method="table", confidence=0.9)

        t_ref = EvidenceRef(source_id="s", source_type="pdf", product_id="T",
                            attribute="full_load_torque_nm", raw_value="7.22", raw_unit="Nm",
                            parsed_value=7.22, method="table", confidence=0.9)
        p_field = NormalizedField(canonical_field="rated_power", canonical_unit="kW",
                                  canonical_value=1.1, outcome=NormalizationOutcome.PASSTHROUGH,
                                  evidence_refs=[ev("rated_power", 1.1, "kW")])
        n_field = NormalizedField(canonical_field="rated_speed", canonical_unit="rpm",
                                  canonical_value=1455.0, outcome=NormalizationOutcome.PASSTHROUGH,
                                  evidence_refs=[ev("rated_speed", 1455.0, "rpm")])
        product = NormalizedProduct(product_id="PIQ-W22SP-4P-TEST", manufacturer="WEG",
                                    model="W22", fields={"rated_power": p_field, "rated_speed": n_field},
                                    unmapped_evidence=[t_ref])

        # Torque check
        findings = check_engineering_torque_power_rpm(product)
        assert findings[0].status.value == "PASS", f"Expected PASS, got {findings[0].status}"

        # Formula verification: T = (P×1000×60)/(2π×N)
        t_expected = (1.1 * 1000 * 60) / (2 * math.pi * 1455)
        assert abs(t_expected - 7.219) < 0.01

        # Synchronous speed check: 4-pole motor at 1455 rpm should PASS
        speed_findings = check_engineering_synchronous_speed(product)
        assert speed_findings[0].status.value == "PASS"

    results.append(_check("Engineering plausibility checks work (torque, synchronous speed)", check_engineering))

    # -----------------------------------------------------------------------
    # 12. Provenance survives validation
    # -----------------------------------------------------------------------
    def check_provenance():
        report_path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "validation_report.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        conflict_findings = [f for f in report["findings"] if f["status"] == "CONFLICT"]
        assert len(conflict_findings) > 0, "Expected at least one CONFLICT finding"
        for finding in conflict_findings:
            assert len(finding["evidence_refs"]) >= 1, (
                f"Conflict finding {finding['rule_id']} has no evidence_refs — provenance lost"
            )
            for ref in finding["evidence_refs"]:
                assert ref["source_type"] in ("pdf", "csv", "web")
                assert ref["raw_value"] != ""

    results.append(_check("Provenance survives validation (evidence_refs in conflict findings)", check_provenance))

    # -----------------------------------------------------------------------
    # 13. All 12 products validated
    # -----------------------------------------------------------------------
    def check_all_products():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        product_ids = [e["product_id"] for e in manifest]
        assert len(product_ids) == 12, f"Expected 12 products, got {len(product_ids)}"
        for pid in product_ids:
            path = PROCESSED_DIR / pid / "validation_report.json"
            assert path.exists(), f"validation_report.json missing for {pid}"
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["product_id"] == pid
            assert len(data["findings"]) > 0

    results.append(_check("All 12 products validated (validation_report.json exists)", check_all_products))

    # -----------------------------------------------------------------------
    # 14. Validation output files exist (per-product + batch)
    # -----------------------------------------------------------------------
    def check_output_files():
        batch_path = PROCESSED_DIR / "batch_validation_report.json"
        assert batch_path.exists(), f"batch_validation_report.json not found"
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        assert batch["products_processed"] == 12

    results.append(_check("Validation output files exist (12 per-product + batch report)", check_output_files))

    # -----------------------------------------------------------------------
    # 15. No fabricated values
    # -----------------------------------------------------------------------
    def check_no_fabrication():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        product_ids = [e["product_id"] for e in manifest]
        for pid in product_ids:
            norm_path = PROCESSED_DIR / pid / "normalized_product.json"
            val_path = PROCESSED_DIR / pid / "validation_report.json"
            norm_data = json.loads(norm_path.read_text(encoding="utf-8"))
            val_data = json.loads(val_path.read_text(encoding="utf-8"))
            for finding in val_data["findings"]:
                if finding["status"] == "CONFLICT":
                    field_name = finding["field"]
                    if field_name in norm_data["fields"]:
                        nf = norm_data["fields"][field_name]
                        assert nf["canonical_value"] is None, (
                            f"{pid}.{field_name}: CONFLICT finding exists but "
                            f"canonical_value={nf['canonical_value']} — fabricated winner!"
                        )

    results.append(_check("No fabricated values (conflicts never have canonical_value set)", check_no_fabrication))

    # -----------------------------------------------------------------------
    # 16. Documentation exists
    # -----------------------------------------------------------------------
    def check_docs():
        docs_dir = PROJECT_ROOT / "docs"
        phase3_md = docs_dir / "PHASE_3.md"
        validation_md = docs_dir / "VALIDATION.md"
        walkthrough = PROJECT_ROOT / "walkthrough.md"
        assert phase3_md.exists(), f"PHASE_3.md not found at {phase3_md}"
        assert validation_md.exists(), f"VALIDATION.md not found at {validation_md}"
        assert walkthrough.exists(), f"walkthrough.md not found"
        # Check Phase 3 is marked COMPLETE in PHASE_3.md
        content = phase3_md.read_text(encoding="utf-8")
        assert "COMPLETE" in content, "PHASE_3.md must contain 'COMPLETE'"

    results.append(_check("Documentation complete (PHASE_3.md, VALIDATION.md, walkthrough.md)", check_docs))

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    passed = sum(results)
    total = len(results)
    print()
    print("=" * 60)
    if passed == total:
        print(f"  PHASE 3 STATUS: COMPLETE [OK]")
        print(f"  All {total} checks passed.")
    else:
        print(f"  PHASE 3 STATUS: INCOMPLETE [{passed}/{total} checks passed]")
    print("=" * 60)
    print()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_checks())
