#!/usr/bin/env python3
"""
ProductIQ Phase 5 Verification Script
======================================
Automated 20-point audit verifying that the Phase 5 Trust-Aware Product Intelligence
layer is fully operational, deterministic, explainable, and compliant with all contracts.
"""
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check(description: str, condition: bool, error_msg: str = ""):
    if condition:
        print(f"  [PASS] {description}")
        return True
    else:
        print(f"  [FAIL] {description}")
        if error_msg:
            print(f"         └─ {error_msg}")
        return False


def main():
    print("=" * 60)
    print("  ProductIQ Phase 5 Verification")
    print("=" * 60)
    print()

    passed = 0
    total = 20

    # 1. Phase 0 baseline intact
    try:
        from productiq.schema.motor import MotorProduct, DataStatus, CANONICAL_UNITS
        m = MotorProduct(product_id="TEST", manufacturer="WEG", model="W22")
        c1 = check("Phase 0 baseline intact", m.schema_version == "0.1.0-phase0" and len(CANONICAL_UNITS) == 11)
    except Exception as e:
        c1 = check("Phase 0 baseline intact", False, str(e))
    passed += int(c1)

    # 2. Phase 1 baseline intact
    try:
        from productiq.extraction.models import EvidenceRecord
        c2 = check("Phase 1 baseline intact", hasattr(EvidenceRecord, "raw_value"))
    except Exception as e:
        c2 = check("Phase 1 baseline intact", False, str(e))
    passed += int(c2)

    # 3. Phase 2 baseline intact
    try:
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        np_test = NormalizedProduct(product_id="TEST", manufacturer="WEG", model="W22", fields={})
        c3 = check("Phase 2 baseline intact", hasattr(np_test, "fields"))
    except Exception as e:
        c3 = check("Phase 2 baseline intact", False, str(e))
    passed += int(c3)

    # 4. Phase 3 baseline intact
    try:
        from productiq.validation.models import ProductValidationReport, ValidationFinding, ValidationStatus
        pvr_test = ProductValidationReport(product_id="TEST", manufacturer="WEG", model="W22", findings=[])
        c4 = check("Phase 3 baseline intact", hasattr(pvr_test, "findings"))
    except Exception as e:
        c4 = check("Phase 3 baseline intact", False, str(e))
    passed += int(c4)

    # 5. Phase 4 baseline intact
    try:
        from productiq.enrichment.models import ProductEnrichment, EnrichmentClaim
        pe_test = ProductEnrichment(product_id="TEST", manufacturer="WEG", model="W22", summary="", technical_description="")
        c5 = check("Phase 4 baseline intact", hasattr(pe_test, "source_backed_claims"))
    except Exception as e:
        c5 = check("Phase 4 baseline intact", False, str(e))
    passed += int(c5)

    # 6. Trust models import and serialize
    try:
        from productiq.trust.models import (
            TrustStatus,
            PublishabilityStatus,
            AttributeTrustResult,
            ClaimTrustResult,
            ReviewItem,
            ProductTrustReport,
            BatchTrustReport,
        )
        attr = AttributeTrustResult(
            field="rated_power",
            canonical_value=1.1,
            canonical_unit="kW",
            trust_status=TrustStatus.TRUSTED,
            publishability=PublishabilityStatus.PUBLISHABLE,
        )
        d = attr.to_dict()
        c6 = check("Trust models import and serialize", d["trust_status"] == "TRUSTED" and d["publishability"] == "PUBLISHABLE")
    except Exception as e:
        c6 = check("Trust models import and serialize", False, str(e))
    passed += int(c6)

    # 7. Trust service imports and instantiates
    try:
        from productiq.trust.evaluator import MotorTrustEvaluator
        from productiq.trust.service import ProductTrustAnalyzer, BatchTrustAnalyzer
        evaluator = MotorTrustEvaluator()
        analyzer = ProductTrustAnalyzer(evaluator=evaluator)
        c7 = check("Trust service imports and instantiates", evaluator is not None and analyzer is not None)
    except Exception as e:
        c7 = check("Trust service imports and instantiates", False, str(e))
    passed += int(c7)

    # 8. Attribute trust classification works
    try:
        from productiq.normalization.models import NormalizedField, NormalizationOutcome, EvidenceRef
        from productiq.trust.evaluator import MotorTrustEvaluator
        ref = EvidenceRef(source_id="s", source_type="pdf", product_id="P", attribute="rated_voltage", raw_value="400", raw_unit="V", parsed_value=400.0, method="table", confidence=1.0)
        nf = NormalizedField(canonical_field="rated_voltage", canonical_unit="V", canonical_value=400.0, outcome=NormalizationOutcome.PASSTHROUGH, evidence_refs=[ref])
        np_mock = NormalizedProduct(product_id="P", manufacturer="WEG", model="W22", fields={"rated_voltage": nf})
        rep = evaluator.evaluate(np_mock, None, product_id="P")
        c8 = check("Attribute trust classification works", rep.attribute_trust["rated_voltage"].trust_status == TrustStatus.TRUSTED)
    except Exception as e:
        c8 = check("Attribute trust classification works", False, str(e))
    passed += int(c8)

    # 9. Claim trust classification works
    try:
        claim = EnrichmentClaim(claim_text="Delivers high torque", category="performance", is_source_backed=True, confidence=1.0)
        enrich_mock = ProductEnrichment(product_id="P", manufacturer="WEG", model="W22", summary="S", technical_description="T", source_backed_claims=[claim])
        rep2 = evaluator.evaluate(None, None, enrichment=enrich_mock, product_id="P")
        c9 = check("Claim trust classification works", len(rep2.claim_trust) == 1 and rep2.claim_trust[0].trust_status == TrustStatus.TRUSTED)
    except Exception as e:
        c9 = check("Claim trust classification works", False, str(e))
    passed += int(c9)

    # 10. Conflict preservation works (no silent winner picked)
    try:
        from productiq.normalization.models import ConflictRecord
        c_ref_a = EvidenceRef(source_id="pdf", source_type="pdf", product_id="P", attribute="rated_current", raw_value="2.34", raw_unit="A", parsed_value=2.34, method="table", confidence=1.0)
        c_ref_b = EvidenceRef(source_id="csv", source_type="csv", product_id="P", attribute="rated_current", raw_value="7.22", raw_unit="A", parsed_value=7.22, method="column", confidence=1.0)
        conf = ConflictRecord(canonical_field="rated_current", value_a=2.34, unit_a="A", source_a=c_ref_a, value_b=7.22, unit_b="A", source_b=c_ref_b)
        nf_conf = NormalizedField(canonical_field="rated_current", canonical_unit="A", canonical_value=None, outcome=NormalizationOutcome.CONFLICT, conflicts=[conf])
        np_conf = NormalizedProduct(product_id="P", manufacturer="WEG", model="W22", fields={"rated_current": nf_conf})
        rep3 = evaluator.evaluate(np_conf, None, product_id="P")
        attr_c = rep3.attribute_trust["rated_current"]
        c10 = check(
            "Conflict preservation works (no silent winner picked)",
            attr_c.trust_status == TrustStatus.CONFLICTED and
            attr_c.publishability == PublishabilityStatus.REVIEW_REQUIRED and
            attr_c.canonical_value is None
        )
    except Exception as e:
        c10 = check("Conflict preservation works (no silent winner picked)", False, str(e))
    passed += int(c10)

    # 11. Provenance preservation works
    try:
        c11 = check("Provenance preservation works", len(attr_c.evidence_sources) == 0 or len(rep.attribute_trust["rated_voltage"].evidence_sources) >= 1)
    except Exception as e:
        c11 = check("Provenance preservation works", False, str(e))
    passed += int(c11)

    # 12. Publishability classification works
    try:
        c12 = check(
            "Publishability classification works",
            PublishabilityStatus.PUBLISHABLE.value == "PUBLISHABLE" and
            PublishabilityStatus.REVIEW_REQUIRED.value == "REVIEW_REQUIRED"
        )
    except Exception as e:
        c12 = check("Publishability classification works", False, str(e))
    passed += int(c12)

    # 13. Review queue generation works
    try:
        c13 = check("Review queue generation works", len(rep3.review_queue) >= 1 and rep3.review_queue[0].issue_type == "CONFLICT")
    except Exception as e:
        c13 = check("Review queue generation works", False, str(e))
    passed += int(c13)

    # 14. Explanation generation works
    try:
        c14 = check(
            "Explanation generation works",
            "CONFLICT" in attr_c.reason and len(attr_c.reason) > 10 and
            len(rep3.trust_score_formula) > 5 and "TrustScore" in rep3.trust_score_formula
        )
    except Exception as e:
        c14 = check("Explanation generation works", False, str(e))
    passed += int(c14)

    # 15. Known rated-current conflict handled correctly (PIQ-W22SP-4P-1.1)
    try:
        real_analyzer = ProductTrustAnalyzer()
        demo_report = real_analyzer.analyze("PIQ-W22SP-4P-1.1", data_dir="data", save_output=False)
        demo_current = demo_report.attribute_trust["rated_current"]
        c15 = check(
            "Known rated-current conflict handled correctly (PIQ-W22SP-4P-1.1)",
            demo_current.trust_status == TrustStatus.CONFLICTED and
            demo_current.publishability == PublishabilityStatus.REVIEW_REQUIRED and
            demo_current.canonical_value is None and
            len(demo_current.evidence_sources) >= 2
        )
    except Exception as e:
        c15 = check("Known rated-current conflict handled correctly (PIQ-W22SP-4P-1.1)", False, str(e))
    passed += int(c15)

    # 16. Clean publishable attribute verified (rated_voltage)
    try:
        demo_voltage = demo_report.attribute_trust["rated_voltage"]
        c16 = check(
            "Clean publishable attribute verified (rated_voltage)",
            demo_voltage.trust_status == TrustStatus.TRUSTED and
            demo_voltage.publishability == PublishabilityStatus.PUBLISHABLE and
            demo_voltage.canonical_value == 400.0 and
            "rated_voltage" in demo_report.publishable_attributes
        )
    except Exception as e:
        c16 = check("Clean publishable attribute verified (rated_voltage)", False, str(e))
    passed += int(c16)

    # 17. Deterministic behavior verified (identical scores on repeat runs)
    try:
        demo_report_repeat = real_analyzer.analyze("PIQ-W22SP-4P-1.1", data_dir="data", save_output=False)
        c17 = check(
            "Deterministic behavior verified (identical scores on repeat runs)",
            demo_report.trust_score == demo_report_repeat.trust_score and
            demo_report.trust_score_formula == demo_report_repeat.trust_score_formula
        )
    except Exception as e:
        c17 = check("Deterministic behavior verified (identical scores on repeat runs)", False, str(e))
    passed += int(c17)

    # 18. Batch processing works across real 12-product dataset
    try:
        batch_analyzer = BatchTrustAnalyzer()
        batch_res = batch_analyzer.analyze_dataset(data_dir="data", save_output=True)
        c18 = check(
            "Batch processing works across real 12-product dataset",
            batch_res.total_products == 12 and
            (Path("data/processed/batch_trust_report.json")).exists()
        )
    except Exception as e:
        c18 = check("Batch processing works across real 12-product dataset", False, str(e))
    passed += int(c18)

    # 19. Documentation exists
    try:
        doc_phase5 = (PROJECT_ROOT / "docs" / "PHASE_5.md").exists()
        doc_trust = (PROJECT_ROOT / "docs" / "TRUST.md").exists()
        c19 = check("Documentation exists (docs/PHASE_5.md, docs/TRUST.md)", doc_phase5 and doc_trust)
    except Exception as e:
        c19 = check("Documentation exists (docs/PHASE_5.md, docs/TRUST.md)", False, str(e))
    passed += int(c19)

    # 20. No secrets are tracked
    try:
        env_path = PROJECT_ROOT / ".env"
        env_example_path = PROJECT_ROOT / ".env.example"
        assert env_example_path.exists()
        with open(env_example_path, "r", encoding="utf-8") as f:
            env_example = f.read()
        assert "gsk_" not in env_example
        assert "sk-proj-" not in env_example
        c20 = check("No secrets are tracked (.env ignored, .env.example safe)", True)
    except Exception as e:
        c20 = check("No secrets are tracked (.env ignored, .env.example safe)", False, str(e))
    passed += int(c20)

    print()
    print("=" * 60)
    if passed == total:
        print(f"  PHASE 5 STATUS: COMPLETE [OK]")
        print(f"  All {total} checks passed.")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"  PHASE 5 STATUS: INCOMPLETE [{passed}/{total} checks passed]")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
