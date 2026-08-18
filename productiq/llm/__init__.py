"""
ProductIQ LLM Package
---------------------
Exposes the LLM client for use across the pipeline.
Phase 0: connectivity only. Phase 4+ will add enrichment strategies.
"""
from .client import LLMAuthError, LLMClient, LLMConnectionError, LLMError, LLMQuotaError

__all__ = ["LLMClient", "LLMError", "LLMAuthError", "LLMConnectionError", "LLMQuotaError"]
