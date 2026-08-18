"""
Trust Scoring Base Interface — PHASE 0 STUB
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict
from productiq.schema import MotorProduct


@dataclass
class TrustScore:
    """Result of a trust scoring evaluation."""
    overall_score: float                    # 0.0 – 1.0
    formula: str                            # Human-readable formula string
    component_scores: Dict[str, float] = field(default_factory=dict)
    explanation: str = ""


class BaseTrustScorer(ABC):
    """Abstract base for trust scoring engines."""

    @abstractmethod
    def score(self, product: MotorProduct) -> TrustScore:
        """
        Compute a trust score for a motor product.

        Must return a TrustScore with a non-empty formula field.
        The formula must be human-readable and displayed in the UI.
        """
        raise NotImplementedError
