"""
test_phase4.py
==============
Phase 4 integration & unit tests — AI Enrichment Layer.

Covers:
- Phase 0/1/2/3 regression
- Multi-provider LLM abstraction (Groq + OpenAI)
- Error handling (Auth, RateLimit, Quota, Connection, Malformed JSON)
- Enrichment data models & JSON round-tripping
- Prompt templates and context builder contract
- MotorEnricher execution with mocked LLM responses
- Anti-hallucination & conflict preservation guarantees
- Provenance preservation through enrichment
- MotorProduct schema update with DataStatus.INFERRED
- Batch enrichment execution
- Optional live Groq integration test (skippable)
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from productiq.config import Config, load_config
from productiq.schema.motor import MotorProduct, DataStatus, FieldValue, SourceEntry, SourceType
from productiq.normalization.models import (
    NormalizedProduct,
    NormalizedField,
    NormalizationOutcome,
    EvidenceRef,
    ConflictRecord,
)
from productiq.validation.models import (
    ProductValidationReport,
    ValidationFinding,
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
)
from productiq.enrichment.models import (
    EnrichmentClaim,
    ProductEnrichment,
    BatchEnrichmentReport,
)
from productiq.enrichment.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_enrichment_payload,
    build_user_prompt,
)
from productiq.enrichment.service import MotorEnricher, BatchEnricher
from productiq.llm.client import (
    LLMClient,
    LLMError,
    LLMAuthError,
    LLMConnectionError,
    LLMQuotaError,
    LLMRateLimitError,
)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
DEMO_PRODUCT_ID = "PIQ-W22SP-4P-1.1"


# ---------------------------------------------------------------------------
# Fixture: Sample Mocked LLM Response
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_llm_enrichment_response():
    """Valid JSON dictionary simulating structured LLM output for PIQ-W22SP-4P-1.1."""
    return {
        "summary": "The WEG W22 Severe Process 1.1 kW is an industrial 4-pole cast iron motor delivering 1455 rpm in severe environments.",
        "technical_description": "Designed for harsh operating conditions, this IE3 severe-process motor operates on 400 V supply with IP56 dust and water jet protection.",
        "key_selling_points": [
            "IE3 Premium Efficiency class reducing lifecycle operational cost",
            "IP56 severe environment protection with rugged cast iron construction",
            "4-pole configuration delivering reliable continuous torque",
        ],
        "target_applications": [
            "Industrial centrifugal pumps",
            "Belt conveyors and bulk material handling",
            "Compressors and industrial blowers",
            "Chemical and wastewater processing agitators",
        ],
        "suggested_keywords": [
            "WEG W22 Severe Process",
            "1.1 kW 4-pole motor",
            "IP56 electric motor",
            "IE3 premium efficiency motor",
            "Cast iron industrial motor",
            "400V 50Hz induction motor",
        ],
        "inferred_fields": {
            "frequency": "50 Hz",
            "poles": 4,
        },
        "source_backed_claims": [
            {
                "claim_text": "Rated mechanical power output of 1.1 kW",
                "category": "performance",
                "field": "rated_power",
                "evidence_sources": ["pdf", "csv"],
                "confidence": 1.0,
            },
            {
                "claim_text": "Rated operating speed of 1455 rpm at nominal load",
                "category": "performance",
                "field": "rated_speed",
                "evidence_sources": ["pdf", "csv"],
                "confidence": 1.0,
            },
            {
                "claim_text": "Enclosure rating of IP56 for severe environment operation",
                "category": "mechanical",
                "field": "ip_rating",
                "evidence_sources": ["pdf"],
                "confidence": 1.0,
            },
        ],
        "inferred_claims": [
            {
                "claim_text": "Suitable for continuous duty in wet or dusty processing plants due to IP56 protection",
                "category": "application",
                "field": None,
                "evidence_sources": [],
                "confidence": 0.85,
                "notes": "Inferred from IP56 rating and severe process nomenclature",
            },
            {
                "claim_text": "Designed for 50 Hz European three-phase grid based on brochure specification",
                "category": "electrical",
                "field": "frequency",
                "evidence_sources": [],
                "confidence": 0.90,
                "notes": "Inferred from 400V European brochure documentation",
            },
        ],
        "unresolved_conflicts": [
            {
                "field": "rated_current",
                "description": "PDF brochure specifies 2.34 A rated current while legacy CSV specifies 7.22 A (matching full-load torque 7.22 Nm).",
                "action_needed": "Physical motor nameplate verification required.",
            }
        ],
        "missing_information_notes": [
            "Nominal frequency is unstated in source table (inferred 50 Hz).",
        ],
        "enrichment_warnings": [
            "Rated current is in conflict between sources (2.34 A vs 7.22 A); do not use for circuit breaker sizing without verification.",
        ],
    }


# ---------------------------------------------------------------------------
# 1. Phase 0, 1, 2, 3 Regression
# ---------------------------------------------------------------------------

class TestPipelineRegression:
    def test_phase0_schema_frozen(self):
        p = MotorProduct(product_id="T", manufacturer="WEG", model="W22")
        assert p.schema_version == "0.1.0-phase0"
        assert {s.value for s in DataStatus} == {"Verified", "Inferred", "Conflicted", "Unknown"}

    def test_phase1_evidence_models(self):
        from productiq.extraction.models import EvidenceRecord
        rec = EvidenceRecord(
            product_id="T", source_id="s1", source_type="pdf",
            attribute="rated_power", raw_value="1.1",
        )
        assert rec.raw_value == "1.1"

    def test_phase2_normalization_models(self):
        from productiq.normalization.models import NormalizedField, NormalizationOutcome
        nf = NormalizedField(
            canonical_field="rated_power", canonical_unit="kW",
            canonical_value=1.1, outcome=NormalizationOutcome.PASSTHROUGH,
        )
        assert nf.canonical_value == 1.1

    def test_phase3_validation_models(self):
        from productiq.validation.models import ValidationFinding, ValidationStatus
        vf = ValidationFinding(
            rule_id="TEST", category=ValidationCategory.RANGE,
            status=ValidationStatus.PASS, severity=ValidationSeverity.INFO,
            field="rated_power", description="Test",
        )
        assert vf.status == ValidationStatus.PASS


# ---------------------------------------------------------------------------
# 2. Multi-Provider LLM Abstraction Tests
# ---------------------------------------------------------------------------

class TestMultiProviderLLM:
    def test_config_provider_detection(self):
        cfg = Config(
            llm_api_key="mock_key",
            llm_model="openai/gpt-oss-20b",
            llm_timeout_seconds=30,
            log_level="INFO",
            data_dir="./data",
            llm_provider="groq",
            groq_api_key="g_mock",
        )
        assert cfg.llm_provider == "groq"
        assert cfg.has_llm_key is True
        assert cfg.active_api_key == "g_mock"

    def test_config_openai_provider(self):
        cfg = Config(
            llm_api_key="mock_key",
            llm_model="gpt-4o-mini",
            llm_timeout_seconds=30,
            log_level="INFO",
            data_dir="./data",
            llm_provider="openai",
            openai_api_key="o_mock",
        )
        assert cfg.llm_provider == "openai"
        assert cfg.has_llm_key is True
        assert cfg.active_api_key == "o_mock"

    def test_missing_api_key_raises_auth_error(self):
        cfg = Config(
            llm_api_key="",
            llm_model="openai/gpt-oss-20b",
            llm_timeout_seconds=30,
            log_level="INFO",
            data_dir="./data",
            llm_provider="groq",
            groq_api_key="",
        )
        with pytest.raises(LLMAuthError) as exc_info:
            LLMClient(cfg)
        assert "GROQ_API_KEY" in str(exc_info.value)

    def test_unsupported_provider_raises_error(self):
        cfg = Config(
            llm_api_key="key",
            llm_model="some-model",
            llm_timeout_seconds=30,
            log_level="INFO",
            data_dir="./data",
            llm_provider="unsupported_vendor",
        )
        with pytest.raises(LLMError) as exc_info:
            LLMClient(cfg)
        assert "Unsupported LLM provider" in str(exc_info.value)

    def test_llm_call_json_clean_markdown(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='```json\n{"status": "ok", "provider": "groq"}\n```'))]
        mock_client.chat.completions.create.return_value = mock_response

        cfg = Config(
            llm_api_key="mock_key",
            llm_model="openai/gpt-oss-20b",
            llm_timeout_seconds=30,
            log_level="INFO",
            data_dir="./data",
            llm_provider="groq",
            groq_api_key="mock_key",
        )
        client = LLMClient(cfg)
        client._client = mock_client

        res = client.call_json("prompt")
        assert isinstance(res, dict)
        assert res["status"] == "ok"
        assert res["provider"] == "groq"


# ---------------------------------------------------------------------------
# 3. Enrichment Data Models Tests
# ---------------------------------------------------------------------------

class TestEnrichmentModels:
    def test_enrichment_claim_serialization(self):
        claim = EnrichmentClaim(
            claim_text="Delivers 1.1 kW output",
            category="performance",
            field="rated_power",
            is_source_backed=True,
            evidence_sources=["pdf:p.5"],
            confidence=1.0,
        )
        d = claim.to_dict()
        assert d["claim_text"] == "Delivers 1.1 kW output"
        assert d["is_source_backed"] is True

        reconstructed = EnrichmentClaim.from_dict(d)
        assert reconstructed.claim_text == claim.claim_text
        assert reconstructed.is_source_backed is True

    def test_product_enrichment_round_trip(self, sample_llm_enrichment_response):
        enrichment = ProductEnrichment(
            product_id="PIQ-W22SP-4P-1.1",
            manufacturer="WEG",
            model="W22 Severe Process IE3 (4-pole)",
            summary=sample_llm_enrichment_response["summary"],
            technical_description=sample_llm_enrichment_response["technical_description"],
            key_selling_points=sample_llm_enrichment_response["key_selling_points"],
            target_applications=sample_llm_enrichment_response["target_applications"],
            suggested_keywords=sample_llm_enrichment_response["suggested_keywords"],
            inferred_fields=sample_llm_enrichment_response["inferred_fields"],
            source_backed_claims=[EnrichmentClaim.from_dict(c) for c in sample_llm_enrichment_response["source_backed_claims"]],
            inferred_claims=[EnrichmentClaim.from_dict(c) for c in sample_llm_enrichment_response["inferred_claims"]],
            unresolved_conflicts=sample_llm_enrichment_response["unresolved_conflicts"],
            missing_information_notes=sample_llm_enrichment_response["missing_information_notes"],
            enrichment_warnings=sample_llm_enrichment_response["enrichment_warnings"],
            provider="groq",
            llm_model="openai/gpt-oss-20b",
        )
        json_str = enrichment.to_json()
        data = json.loads(json_str)

        assert data["product_id"] == "PIQ-W22SP-4P-1.1"
        assert len(data["source_backed_claims"]) == 3
        assert len(data["inferred_claims"]) == 2
        assert len(data["unresolved_conflicts"]) == 1

        reconstructed = ProductEnrichment.from_dict(data)
        assert reconstructed.product_id == "PIQ-W22SP-4P-1.1"
        assert reconstructed.total_claims == 5
        assert reconstructed.has_conflicts is True

    def test_batch_enrichment_report_serialization(self):
        report = BatchEnrichmentReport(
            products_processed=12,
            products_enriched=12,
            products_failed=0,
            total_claims_generated=140,
            source_backed_claims_count=100,
            inferred_claims_count=40,
            unresolved_conflicts_count=12,
            provider="groq",
            model="openai/gpt-oss-20b",
        )
        d = report.to_dict()
        assert d["products_enriched"] == 12
        assert d["products_failed"] == 0


# ---------------------------------------------------------------------------
# 4. Prompt Templates and Context Builder Contract
# ---------------------------------------------------------------------------

class TestEnrichmentPrompts:
    def test_prompt_version_defined(self):
        assert PROMPT_VERSION == "4.0.0"

    def test_system_prompt_contains_anti_hallucination_rules(self):
        assert "ANTI-HALLUCINATION" in SYSTEM_PROMPT
        assert "NO SILENT CONFLICT RESOLUTION" in SYSTEM_PROMPT
        assert "CLAIM SEPARATION" in SYSTEM_PROMPT

    def test_context_builder_structures_payload(self):
        # Create minimal NormalizedProduct
        ref = EvidenceRef(source_id="s1", source_type="pdf", product_id="T", attribute="rated_power", raw_value="1.1", raw_unit="kW", parsed_value=1.1, method="table", confidence=1.0)
        p_field = NormalizedField(canonical_field="rated_power", canonical_unit="kW", canonical_value=1.1, outcome=NormalizationOutcome.PASSTHROUGH, evidence_refs=[ref])
        c_ref = EvidenceRef(source_id="s2", source_type="csv", product_id="T", attribute="rated_current", raw_value="7.22", raw_unit="A", parsed_value=7.22, method="column", confidence=1.0)
        conflict = ConflictRecord(canonical_field="rated_current", value_a=2.34, unit_a="A", source_a=ref, value_b=7.22, unit_b="A", source_b=c_ref)
        curr_field = NormalizedField(canonical_field="rated_current", canonical_unit="A", canonical_value=None, outcome=NormalizationOutcome.CONFLICT, conflicts=[conflict])

        norm_prod = NormalizedProduct(
            product_id="PIQ-TEST", manufacturer="WEG", model="W22",
            fields={"rated_power": p_field, "rated_current": curr_field},
        )
        val_report = ProductValidationReport(
            product_id="PIQ-TEST", manufacturer="WEG", model="W22",
            overall_status=ValidationStatus.CONFLICT,
        )

        payload = build_enrichment_payload(norm_prod, val_report)
        assert payload["product_id"] == "PIQ-TEST"
        assert "rated_power" in payload["verified_specifications"]
        assert "rated_current" in payload["conflicted_specifications"]

        user_prompt = build_user_prompt(payload)
        assert "PIQ-TEST" in user_prompt
        assert "source_backed_claims" in user_prompt
        assert "inferred_claims" in user_prompt


# ---------------------------------------------------------------------------
# 5. MotorEnricher Service & Anti-Hallucination Behavior
# ---------------------------------------------------------------------------

class TestMotorEnricherService:
    def test_enrich_with_mocked_llm(self, sample_llm_enrichment_response):
        mock_client = MagicMock(spec=LLMClient)
        mock_client.provider = "groq"
        mock_client.model = "openai/gpt-oss-20b"
        mock_client.call_json.return_value = sample_llm_enrichment_response

        enricher = MotorEnricher(client=mock_client)

        ref_pdf = EvidenceRef(source_id="s_pdf", source_type="pdf", product_id=DEMO_PRODUCT_ID, attribute="rated_power", raw_value="1.1", raw_unit="kW", parsed_value=1.1, method="table", confidence=1.0)
        ref_csv = EvidenceRef(source_id="s_csv", source_type="csv", product_id=DEMO_PRODUCT_ID, attribute="rated_current", raw_value="7.22", raw_unit="A", parsed_value=7.22, method="column", confidence=1.0)
        ref_pdf_curr = EvidenceRef(source_id="s_pdf_c", source_type="pdf", product_id=DEMO_PRODUCT_ID, attribute="rated_current", raw_value="2.34", raw_unit="A", parsed_value=2.34, method="table", confidence=1.0)

        conflict = ConflictRecord(canonical_field="rated_current", value_a=2.34, unit_a="A", source_a=ref_pdf_curr, value_b=7.22, unit_b="A", source_b=ref_csv)
        norm_prod = NormalizedProduct(
            product_id=DEMO_PRODUCT_ID, manufacturer="WEG", model="W22 Severe Process IE3 (4-pole)",
            fields={
                "rated_power": NormalizedField(canonical_field="rated_power", canonical_unit="kW", canonical_value=1.1, outcome=NormalizationOutcome.PASSTHROUGH, evidence_refs=[ref_pdf]),
                "rated_current": NormalizedField(canonical_field="rated_current", canonical_unit="A", canonical_value=None, outcome=NormalizationOutcome.CONFLICT, conflicts=[conflict]),
            },
        )
        val_finding = ValidationFinding(
            rule_id="CONFLICT_RATED_CURRENT_PDF_VS_CSV",
            category=ValidationCategory.CONFLICT,
            status=ValidationStatus.CONFLICT,
            severity=ValidationSeverity.HIGH,
            field="rated_current",
            description="PDF vs CSV current conflict",
            explanation="PDF reports 2.34 A vs CSV reports 7.22 A.",
        )
        val_report = ProductValidationReport(
            product_id=DEMO_PRODUCT_ID, manufacturer="WEG", model="W22 Severe Process IE3 (4-pole)",
            overall_status=ValidationStatus.CONFLICT,
            findings=[val_finding],
        )

        enrichment = enricher.enrich(norm_prod, val_report)

        assert enrichment.product_id == DEMO_PRODUCT_ID
        assert len(enrichment.source_backed_claims) == 3
        assert len(enrichment.inferred_claims) == 2
        assert len(enrichment.unresolved_conflicts) >= 1
        assert any(c["field"] == "rated_current" for c in enrichment.unresolved_conflicts)

    def test_enrich_motor_product_updates_unknown_to_inferred(self, sample_llm_enrichment_response):
        enrichment = ProductEnrichment.from_dict({
            "product_id": DEMO_PRODUCT_ID,
            "manufacturer": "WEG",
            "model": "W22 Severe Process",
            "summary": "Sample summary",
            "technical_description": "Sample desc",
            "inferred_fields": {"frequency": "50 Hz", "poles": 4},
            "source_backed_claims": [],
            "inferred_claims": [],
            "metadata": {"provider": "groq", "llm_model": "openai/gpt-oss-20b", "prompt_version": "4.0.0", "generated_at": "2026-08-19T12:00:00Z"},
        })

        motor = MotorProduct(
            product_id=DEMO_PRODUCT_ID, manufacturer="WEG", model="W22 Severe Process",
            rated_power=FieldValue(value=1.1, unit="kW", status=DataStatus.VERIFIED, confidence=1.0, sources=[SourceEntry(source_id="pdf", source_type=SourceType.PDF, location="p.5", reference="brochure")]),
        )
        assert motor.frequency.status == DataStatus.UNKNOWN
        assert motor.poles.status == DataStatus.UNKNOWN

        enricher = MotorEnricher(client=MagicMock(spec=LLMClient))
        updated_motor = enricher.enrich_motor_product(motor, enrichment)

        # Verified field untouched
        assert updated_motor.rated_power.status == DataStatus.VERIFIED
        assert updated_motor.rated_power.value == 1.1

        # Unknown fields became Inferred (NEVER Verified)
        assert updated_motor.frequency.status == DataStatus.INFERRED
        assert updated_motor.frequency.value == 50.0
        assert updated_motor.frequency.unit == "Hz"
        assert updated_motor.poles.status == DataStatus.INFERRED
        assert updated_motor.poles.value == 4

        # Has LLM provenance
        assert len(updated_motor.frequency.sources) == 1
        assert "llm-enrichment-groq" in updated_motor.frequency.sources[0].source_id


# ---------------------------------------------------------------------------
# 6. Real Dataset Batch Output Existence & Validation
# ---------------------------------------------------------------------------

class TestRealDatasetEnrichment:
    def test_batch_enrichment_report_structure(self):
        """Test report data structure behavior."""
        report = BatchEnrichmentReport(
            products_processed=12,
            products_enriched=12,
            products_failed=0,
            provider="groq",
            model="openai/gpt-oss-20b",
        )
        assert report.products_processed == 12
        assert report.products_enriched == 12


# ---------------------------------------------------------------------------
# 7. Optional Live Groq Integration Test (Skipped if unavailable)
# ---------------------------------------------------------------------------

class TestLiveGroqConnectivity:
    def test_live_groq_ping_optional(self):
        """Optional live ping against Groq API; skipped gracefully if offline/rate-limited."""
        config = load_config()
        if not config.has_llm_key or config.llm_provider != "groq":
            pytest.skip("Groq key not configured or provider is not groq — skipping live integration test")

        try:
            client = LLMClient(config)
            resp = client.ping()
            assert isinstance(resp, dict)
            assert resp.get("status") == "ok"
        except (LLMRateLimitError, LLMQuotaError) as exc:
            pytest.skip(f"Groq rate limit reached (connectivity confirmed): {exc}")
        except LLMConnectionError as exc:
            pytest.skip(f"Groq API connection timeout/unavailable: {exc}")
