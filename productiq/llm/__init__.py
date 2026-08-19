"""
ProductIQ LLM Module
====================
Multi-provider LLM abstraction layer for ProductIQ.
Supports Groq (primary) and OpenAI (optional).
"""
from productiq.llm.client import (
    LLMClient,
    LLMError,
    LLMAuthError,
    LLMConnectionError,
    LLMQuotaError,
    LLMRateLimitError,
)

__all__ = [
    "LLMClient",
    "LLMError",
    "LLMAuthError",
    "LLMConnectionError",
    "LLMQuotaError",
    "LLMRateLimitError",
]
