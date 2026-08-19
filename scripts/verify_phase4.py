"""
ProductIQ Phase 4 Verification Script
=======================================
18-point automated audit of the Phase 4 AI enrichment engine.

Usage:
    python scripts/verify_phase4.py
    python -X utf8 scripts/verify_phase4.py

Expected result:
    PHASE 4 STATUS: COMPLETE [OK]
    All 18 checks passed.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

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
    print("  ProductIQ Phase 4 Verification")
    print("=" * 60)
    print()

    results = []

    # 1. Phase 0 baseline intact
    def check_phase0():
        from productiq.schema import CANONICAL_UNITS, DataStatus, MotorProduct
        assert len(CANONICAL_UNITS) == 11
        assert {s.value for s in DataStatus} == {"Verified", "Inferred", "Conflicted", "Unknown"}
        p = MotorProduct(product_id="t", manufacturer="t", model="t")
        assert p.schema_version == "0.1.0-phase0"

    results.append(_check("Phase 0 baseline intact", check_phase0))

    # 2. Phase 1 baseline intact
    def check_phase1():
        from productiq.extraction.models import EvidenceRecord, ExtractionResult
        from productiq.extraction.pdf_extractor import PDFExtractor
        from productiq.extraction.csv_extractor import CSVExtractor
        assert EvidenceRecord is not None
        assert PDFExtractor is not None
        assert CSVExtractor is not None

    results.append(_check("Phase 1 baseline intact", check_phase1))

    # 3. Phase 2 baseline intact
    def check_phase2():
        from productiq.normalization import MotorNormalizer, NormalizedProduct
        assert MotorNormalizer is not None
        norm_path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "normalized_product.json"
        assert norm_path.exists(), f"normalized_product.json missing: {norm_path}"

    results.append(_check("Phase 2 baseline intact", check_phase2))

    # 4. Phase 3 baseline intact
    def check_phase3():
        from productiq.validation import MotorValidator, ProductValidationReport
        assert MotorValidator is not None
        val_path = PROCESSED_DIR / "PIQ-W22SP-4P-1.1" / "validation_report.json"
        assert val_path.exists(), f"validation_report.json missing: {val_path}"
        val_data = json.loads(val_path.read_text(encoding="utf-8"))
        assert "findings" in val_data

    results.append(_check("Phase 3 baseline intact", check_phase3))

    # 5. LLM provider abstraction exists
    def check_provider_abstraction():
        from productiq.llm import LLMClient, LLMError, LLMAuthError, LLMRateLimitError
        assert LLMClient is not None
        assert LLMAuthError is not None

    results.append(_check("LLM provider abstraction exists", check_provider_abstraction))

    # 6. Groq provider configuration exists
    def check_groq_config():
        from productiq.config import Config
        cfg = Config(
            llm_api_key="mock", llm_model="openai/gpt-oss-20b",
            llm_timeout_seconds=30, log_level="INFO", data_dir="./data",
            llm_provider="groq", groq_api_key="mock_groq",
        )
        assert cfg.llm_provider == "groq"
        assert cfg.has_llm_key is True

    results.append(_check("Groq provider configuration exists", check_groq_config))

    # 7. OpenAI compatibility remains
    def check_openai_config():
        from productiq.config import Config
        cfg = Config(
            llm_api_key="mock", llm_model="gpt-4o-mini",
            llm_timeout_seconds=30, log_level="INFO", data_dir="./data",
            llm_provider="openai", openai_api_key="mock_openai",
        )
        assert cfg.llm_provider == "openai"
        assert cfg.has_llm_key is True

    results.append(_check("OpenAI compatibility remains", check_openai_config))

    # 8. Enrichment models import
    def check_models_import():
        from productiq.enrichment import (
            EnrichmentClaim,
            ProductEnrichment,
            BatchEnrichmentReport,
        )
        assert EnrichmentClaim is not None
        assert ProductEnrichment is not None
        assert BatchEnrichmentReport is not None

    results.append(_check("Enrichment models import", check_models_import))

    # 9. Enrichment service imports
    def check_service_import():
        from productiq.enrichment import MotorEnricher, BatchEnricher
        assert MotorEnricher is not None
        assert BatchEnricher is not None

    results.append(_check("Enrichment service imports", check_service_import))

    # 10. Prompt contract exists
    def check_prompt_contract():
        from productiq.enrichment.prompts import (
            PROMPT_VERSION, SYSTEM_PROMPT, build_enrichment_payload, build_user_prompt
        )
        assert PROMPT_VERSION == "4.0.0"
        assert "ANTI-HALLUCINATION" in SYSTEM_PROMPT
        assert "NO SILENT CONFLICT RESOLUTION" in SYSTEM_PROMPT

    results.append(_check("Prompt contract exists", check_prompt_contract))

    # 11. Structured output works
    def check_structured_output():
        from productiq.enrichment.models import EnrichmentClaim, ProductEnrichment
        c = EnrichmentClaim(claim_text="Test", category="performance", is_source_backed=True)
        pe = ProductEnrichment(
            product_id="T", manufacturer="WEG", model="W22",
            summary="S", technical_description="TD",
            source_backed_claims=[c],
        )
        j = pe.to_json()
        pe_reconstructed = ProductEnrichment.from_dict(json.loads(j))
        assert pe_reconstructed.product_id == "T"
        assert len(pe_reconstructed.source_backed_claims) == 1

    results.append(_check("Structured output works", check_structured_output))

    # 12. Mock enrichment works
    def check_mock_enrichment():
        from productiq.enrichment.service import MotorEnricher
        from productiq.llm.client import LLMClient
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome
        from productiq.validation.models import ProductValidationReport, ValidationStatus

        mock_client = MagicMock(spec=LLMClient)
        mock_client.provider = "groq"
        mock_client.model = "openai/gpt-oss-20b"
        mock_client.call_json.return_value = {
            "summary": "Mock summary",
            "technical_description": "Mock desc",
            "key_selling_points": ["Point 1"],
            "target_applications": ["Pumps"],
            "suggested_keywords": ["Keyword"],
            "inferred_fields": {"frequency": "50 Hz", "poles": 4},
            "source_backed_claims": [{"claim_text": "1.1 kW", "category": "performance", "field": "rated_power", "evidence_sources": ["pdf"]}],
            "inferred_claims": [{"claim_text": "Inferred pump use", "category": "application", "confidence": 0.85}],
            "unresolved_conflicts": [],
            "missing_information_notes": [],
            "enrichment_warnings": [],
        }
        enricher = MotorEnricher(client=mock_client)
        p_field = NormalizedField(canonical_field="rated_power", canonical_unit="kW", canonical_value=1.1, outcome=NormalizationOutcome.PASSTHROUGH)
        prod = NormalizedProduct(product_id="PIQ-MOCK", manufacturer="WEG", model="W22", fields={"rated_power": p_field})
        val = ProductValidationReport(product_id="PIQ-MOCK", manufacturer="WEG", model="W22", overall_status=ValidationStatus.PASS)

        res = enricher.enrich(prod, val)
        assert res.summary == "Mock summary"
        assert len(res.source_backed_claims) == 1

    results.append(_check("Mock enrichment works", check_mock_enrichment))

    # 13. Conflict handling works
    def check_conflict_handling():
        from productiq.enrichment.service import MotorEnricher
        from productiq.llm.client import LLMClient
        from productiq.normalization.models import NormalizedProduct, NormalizedField, NormalizationOutcome, ConflictRecord, EvidenceRef
        from productiq.validation.models import ProductValidationReport, ValidationStatus, ValidationFinding, ValidationSeverity, ValidationCategory

        mock_client = MagicMock(spec=LLMClient)
        mock_client.provider = "groq"
        mock_client.model = "openai/gpt-oss-20b"
        mock_client.call_json.return_value = {
            "summary": "Summary with conflict",
            "technical_description": "Desc",
            "key_selling_points": [],
            "target_applications": [],
            "suggested_keywords": [],
            "inferred_fields": {},
            "source_backed_claims": [],
            "inferred_claims": [],
            "unresolved_conflicts": [],  # LLM omitted conflict
            "missing_information_notes": [],
            "enrichment_warnings": [],
        }
        enricher = MotorEnricher(client=mock_client)
        ref1 = EvidenceRef(source_id="pdf", source_type="pdf", product_id="PIQ-C", attribute="rated_current", raw_value="2.34", raw_unit="A", parsed_value=2.34, method="table", confidence=1.0)
        ref2 = EvidenceRef(source_id="csv", source_type="csv", product_id="PIQ-C", attribute="rated_current", raw_value="7.22", raw_unit="A", parsed_value=7.22, method="column", confidence=1.0)
        conflict = ConflictRecord(canonical_field="rated_current", value_a=2.34, unit_a="A", source_a=ref1, value_b=7.22, unit_b="A", source_b=ref2)
        c_field = NormalizedField(canonical_field="rated_current", canonical_unit="A", canonical_value=None, outcome=NormalizationOutcome.CONFLICT, conflicts=[conflict])
        prod = NormalizedProduct(product_id="PIQ-C", manufacturer="WEG", model="W22", fields={"rated_current": c_field})

        val = ProductValidationReport(
            product_id="PIQ-C", manufacturer="WEG", model="W22", overall_status=ValidationStatus.CONFLICT,
            findings=[ValidationFinding(
                rule_id="CONFLICT_RATED_CURRENT_PDF_VS_CSV", category=ValidationCategory.CONFLICT,
                status=ValidationStatus.CONFLICT, severity=ValidationSeverity.HIGH,
                field="rated_current", description="Discrepancy", explanation="2.34 vs 7.22 A",
            )],
        )

        res = enricher.enrich(prod, val)
        # Verify conflict was preserved by post-processor even if omitted by LLM
        assert len(res.unresolved_conflicts) >= 1
        assert any(c["field"] == "rated_current" for c in res.unresolved_conflicts)

    results.append(_check("Conflict handling works", check_conflict_handling))

    # 14. Provenance is preserved
    def check_provenance_preserved():
        from productiq.schema.motor import MotorProduct, DataStatus
        from productiq.enrichment.models import ProductEnrichment
        from productiq.enrichment.service import MotorEnricher
        from productiq.llm.client import LLMClient

        enrichment = ProductEnrichment.from_dict({
            "product_id": "PIQ-PROV", "manufacturer": "WEG", "model": "W22",
            "summary": "S", "technical_description": "TD",
            "inferred_fields": {"frequency": "50 Hz", "poles": 4},
            "source_backed_claims": [], "inferred_claims": [],
            "metadata": {"provider": "groq", "llm_model": "openai/gpt-oss-20b", "prompt_version": "4.0.0", "generated_at": "2026-08-19T00:00:00Z"},
        })
        motor = MotorProduct(product_id="PIQ-PROV", manufacturer="WEG", model="W22")
        enricher = MotorEnricher(client=MagicMock(spec=LLMClient))
        updated = enricher.enrich_motor_product(motor, enrichment)

        assert updated.frequency.status == DataStatus.INFERRED
        assert len(updated.frequency.sources) == 1
        assert "llm-enrichment-groq" in updated.frequency.sources[0].source_id
        assert "prompt_version_4.0.0" in updated.frequency.sources[0].location

    results.append(_check("Provenance is preserved", check_provenance_preserved))

    # 15. Security configuration is valid
    def check_security_config():
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert ".env" in gitignore or "*.env" in gitignore
        env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        assert "GROQ_API_KEY=" in env_example or "LLM_API_KEY=" in env_example
        # Make sure no raw secret strings are in .env.example
        assert "gsk_" not in env_example
        assert "sk-proj-" not in env_example

    results.append(_check("Security configuration is valid", check_security_config))

    # 16. Documentation exists
    def check_docs():
        docs_dir = PROJECT_ROOT / "docs"
        phase4_md = docs_dir / "PHASE_4.md"
        enrichment_md = docs_dir / "ENRICHMENT.md"
        assert phase4_md.exists(), f"PHASE_4.md not found at {phase4_md}"
        assert enrichment_md.exists(), f"ENRICHMENT.md not found at {enrichment_md}"
        content = phase4_md.read_text(encoding="utf-8")
        assert "COMPLETE" in content

    results.append(_check("Documentation exists", check_docs))

    # 17. No secrets are tracked
    def check_no_secrets_tracked():
        import subprocess
        res = subprocess.run(["git", "ls-files"], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        tracked_files = res.stdout.splitlines()
        for f in tracked_files:
            assert not f.endswith(".env"), f"Secret file {f} is tracked in Git!"
            assert not f.endswith(".pyc"), f"Compiled cache {f} is tracked in Git!"

    results.append(_check("No secrets are tracked", check_no_secrets_tracked))

    # 18. Real dataset enrichment pipeline executes using mocked LLM
    def check_real_dataset_mock_pipeline():
        from productiq.enrichment.service import BatchEnricher, MotorEnricher
        from productiq.llm.client import LLMClient

        mock_client = MagicMock(spec=LLMClient)
        mock_client.provider = "groq"
        mock_client.model = "openai/gpt-oss-20b"
        mock_client.call_json.return_value = {
            "summary": "Industrial motor commercial summary.",
            "technical_description": "Detailed engineering description.",
            "key_selling_points": ["IE3 Efficiency", "IP56 Protection"],
            "target_applications": ["Pumps", "Fans", "Conveyors"],
            "suggested_keywords": ["WEG W22", "Industrial Motor", "IE3"],
            "inferred_fields": {"frequency": "50 Hz", "poles": 4},
            "source_backed_claims": [{"claim_text": "1.1 kW output", "category": "performance", "field": "rated_power", "evidence_sources": ["pdf"]}],
            "inferred_claims": [{"claim_text": "Continuous pump duty", "category": "application", "confidence": 0.85}],
            "unresolved_conflicts": [],
            "missing_information_notes": [],
            "enrichment_warnings": [],
        }
        enricher = MotorEnricher(client=mock_client)
        batch = BatchEnricher(data_dir=DATA_DIR, enricher=enricher)
        report = batch.run_all()
        assert report.products_processed == 12
        assert report.products_enriched == 12
        assert report.products_failed == 0

    results.append(_check("Real dataset enrichment pipeline executes using mocked LLM", check_real_dataset_mock_pipeline))

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    passed = sum(results)
    total = len(results)
    print()
    print("=" * 60)
    if passed == total:
        print(f"  PHASE 4 STATUS: COMPLETE [OK]")
        print(f"  All {total} checks passed.")
    else:
        print(f"  PHASE 4 STATUS: INCOMPLETE [{passed}/{total} checks passed]")
    print("=" * 60)
    print()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_checks())
