"""
ProductIQ Trust-Aware Product Intelligence Module — Phase 5
============================================================
Explainable, deterministic trust evaluation and publishability analysis
for industrial equipment product intelligence.
"""
from productiq.trust.base import TrustScore, BaseTrustScorer
from productiq.trust.models import (
    TrustStatus,
    PublishabilityStatus,
    AttributeTrustResult,
    ClaimTrustResult,
    ReviewItem,
    ProductTrustReport,
    BatchTrustReport,
)
from productiq.trust.evaluator import MotorTrustEvaluator
from productiq.trust.service import ProductTrustAnalyzer, BatchTrustAnalyzer

__all__ = [
    "TrustScore",
    "BaseTrustScorer",
    "TrustStatus",
    "PublishabilityStatus",
    "AttributeTrustResult",
    "ClaimTrustResult",
    "ReviewItem",
    "ProductTrustReport",
    "BatchTrustReport",
    "MotorTrustEvaluator",
    "ProductTrustAnalyzer",
    "BatchTrustAnalyzer",
]
