"""
Enrichment Base Interface — PHASE 0 STUB
"""
from abc import ABC, abstractmethod
from productiq.schema import MotorProduct


class BaseEnricher(ABC):
    """Abstract base for LLM-grounded field enrichment."""

    @abstractmethod
    def enrich(self, product: MotorProduct) -> MotorProduct:
        """
        Enrich Unknown fields in a motor product using LLM reasoning.

        MUST:
        - Only process fields where status == Unknown
        - Set enriched fields to status=Inferred (never Verified)
        - Record LLM model, prompt version, and timestamp in SourceEntry
        - Never overwrite Verified or Inferred fields

        Returns updated MotorProduct with enriched fields.
        """
        raise NotImplementedError
