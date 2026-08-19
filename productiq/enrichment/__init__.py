"""
ProductIQ Enrichment Module — Phase 4
=====================================
Transforms validated motor product intelligence into structured,
commerce-ready commercial intelligence via grounded LLM reasoning.

Public API:
    from productiq.enrichment import (
        MotorEnricher,
        BatchEnricher,
        ProductEnrichment,
        EnrichmentClaim,
        BatchEnrichmentReport,
    )
"""
from productiq.enrichment.base import BaseEnricher
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
from productiq.enrichment.service import (
    MotorEnricher,
    BatchEnricher,
)

__all__ = [
    "BaseEnricher",
    "EnrichmentClaim",
    "ProductEnrichment",
    "BatchEnrichmentReport",
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "build_enrichment_payload",
    "build_user_prompt",
    "MotorEnricher",
    "BatchEnricher",
]
