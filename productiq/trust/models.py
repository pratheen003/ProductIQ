"""
ProductIQ Trust Models — Phase 5
=================================
Data structures for explainable, trust-aware product intelligence.

Architectural guarantees:
- Attribute trust is independently derived from Phase 2 (normalization) and Phase 3 (validation).
- Claim trust evaluates Phase 4 AI enrichment outputs against source evidence and validation contracts.
- No silent conflict resolution: conflicted fields remain CONFLICTED with REVIEW_REQUIRED publishability.
- Every trust decision carries human-readable explanations, rule references, and evidence provenance.
- Trust scores are strictly deterministic with visible mathematical formulas.
"""
from __future__ import annotations

import dataclasses as dc
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Trust Status Enum
# ---------------------------------------------------------------------------

class TrustStatus(str, Enum):
    """Trust classification for an individual attribute, claim, or product."""
    TRUSTED         = "TRUSTED"          # Verified by multiple/primary sources and passed validation
    REVIEW_REQUIRED = "REVIEW_REQUIRED"  # Flagged with validation warning or requires human confirmation
    CONFLICTED      = "CONFLICTED"       # Multiple sources disagree; no winner picked
    UNVERIFIED      = "UNVERIFIED"       # Inferred by LLM or unvalidated without direct ground truth
    UNSUPPORTED     = "UNSUPPORTED"      # Contradicted by engineering checks or failed validation
    MISSING         = "MISSING"          # Field is absent / Unknown across all sources


# ---------------------------------------------------------------------------
# Publishability Status Enum
# ---------------------------------------------------------------------------

class PublishabilityStatus(str, Enum):
    """Commerce readiness classification for downstream catalog publication."""
    PUBLISHABLE              = "PUBLISHABLE"               # Safe to publish as verified specification
    PUBLISHABLE_WITH_WARNING = "PUBLISHABLE_WITH_WARNING"  # Safe to publish with inferred / warning disclaimer
    REVIEW_REQUIRED          = "REVIEW_REQUIRED"           # Blocked from auto-publishing until human review
    NOT_PUBLISHABLE          = "NOT_PUBLISHABLE"           # Missing or untrusted; do not publish


# ---------------------------------------------------------------------------
# Attribute-Level Trust Result
# ---------------------------------------------------------------------------

@dc.dataclass
class AttributeTrustResult:
    """
    Independent trust evaluation for a single canonical technical field.
    Derived strictly from Phase 2 Normalization and Phase 3 Validation.
    """
    field: str
    canonical_value: Optional[Any]
    canonical_unit: Optional[str]
    trust_status: TrustStatus
    publishability: PublishabilityStatus
    validation_status: Optional[str] = None       # "PASS", "WARNING", "CONFLICT", "FAIL", "NOT_CHECKED"
    is_conflicted: bool = False
    evidence_sources: List[str] = dc.field(default_factory=list)
    confidence_score: float = 1.0                # Deterministic confidence [0.0 - 1.0]
    reason: str = ""
    validation_rule_ids: List[str] = dc.field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "canonical_value": self.canonical_value,
            "canonical_unit": self.canonical_unit,
            "trust_status": self.trust_status.value,
            "publishability": self.publishability.value,
            "validation_status": self.validation_status,
            "is_conflicted": self.is_conflicted,
            "evidence_sources": self.evidence_sources,
            "confidence_score": self.confidence_score,
            "reason": self.reason,
            "validation_rule_ids": self.validation_rule_ids,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AttributeTrustResult:
        return cls(
            field=data["field"],
            canonical_value=data.get("canonical_value"),
            canonical_unit=data.get("canonical_unit"),
            trust_status=TrustStatus(data["trust_status"]),
            publishability=PublishabilityStatus(data["publishability"]),
            validation_status=data.get("validation_status"),
            is_conflicted=data.get("is_conflicted", False),
            evidence_sources=data.get("evidence_sources", []),
            confidence_score=float(data.get("confidence_score", 1.0)),
            reason=data.get("reason", ""),
            validation_rule_ids=data.get("validation_rule_ids", []),
        )


# ---------------------------------------------------------------------------
# Claim-Level Trust Result
# ---------------------------------------------------------------------------

@dc.dataclass
class ClaimTrustResult:
    """
    Trust evaluation of an AI-generated enrichment claim against evidence and validation.
    """
    claim_text: str
    category: str                                 # "performance", "application", "mechanical", etc.
    claim_type: str                               # "SOURCE_BACKED", "INFERRED", "UNSUPPORTED"
    trust_status: TrustStatus
    publishability: PublishabilityStatus
    supporting_fields: List[str] = dc.field(default_factory=list)
    evidence_sources: List[str] = dc.field(default_factory=list)
    confidence: float = 1.0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "category": self.category,
            "claim_type": self.claim_type,
            "trust_status": self.trust_status.value,
            "publishability": self.publishability.value,
            "supporting_fields": self.supporting_fields,
            "evidence_sources": self.evidence_sources,
            "confidence": self.confidence,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ClaimTrustResult:
        return cls(
            claim_text=data["claim_text"],
            category=data.get("category", "general"),
            claim_type=data.get("claim_type", "INFERRED"),
            trust_status=TrustStatus(data["trust_status"]),
            publishability=PublishabilityStatus(data["publishability"]),
            supporting_fields=data.get("supporting_fields", []),
            evidence_sources=data.get("evidence_sources", []),
            confidence=float(data.get("confidence", 1.0)),
            reason=data.get("reason", ""),
        )


# ---------------------------------------------------------------------------
# Review Queue Item
# ---------------------------------------------------------------------------

@dc.dataclass
class ReviewItem:
    """
    Structured action item for catalog engineers / human reviewers.
    """
    review_id: str                               # e.g. "REV-PIQ-W22SP-4P-1.1-rated_current"
    target_type: str                             # "attribute", "claim", "engineering"
    target_name: str                             # Field or claim identifier
    severity: str                                # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    issue_type: str                              # "CONFLICT", "WARNING", "FAIL", "UNVERIFIED_INFERENCE", "MISSING_DATA"
    description: str                             # Comprehensive description of the issue
    conflicting_values: Optional[List[Dict[str, Any]]] = None # Detailed source breakdown
    validation_rule_id: Optional[str] = None
    affected_claims: List[str] = dc.field(default_factory=list)
    recommended_action: str = ""

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "target_type": self.target_type,
            "target_name": self.target_name,
            "severity": self.severity,
            "issue_type": self.issue_type,
            "description": self.description,
            "conflicting_values": self.conflicting_values,
            "validation_rule_id": self.validation_rule_id,
            "affected_claims": self.affected_claims,
            "recommended_action": self.recommended_action,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReviewItem:
        return cls(
            review_id=data["review_id"],
            target_type=data["target_type"],
            target_name=data["target_name"],
            severity=data["severity"],
            issue_type=data["issue_type"],
            description=data["description"],
            conflicting_values=data.get("conflicting_values"),
            validation_rule_id=data.get("validation_rule_id"),
            affected_claims=data.get("affected_claims", []),
            recommended_action=data.get("recommended_action", ""),
        )


# ---------------------------------------------------------------------------
# Product Trust Report
# ---------------------------------------------------------------------------

@dc.dataclass
class ProductTrustReport:
    """
    Complete explainable trust report for a single motor product.
    """
    product_id: str
    manufacturer: str
    model: str
    overall_trust_status: TrustStatus
    overall_publishability: PublishabilityStatus
    trust_score: float                           # Deterministic composite score [0.0 - 1.0]
    trust_score_formula: str                     # Human-readable rendered mathematical formula
    trust_score_breakdown: Dict[str, float]      # Component score contributions
    attribute_trust: Dict[str, AttributeTrustResult]
    claim_trust: List[ClaimTrustResult]
    review_queue: List[ReviewItem]
    unresolved_conflicts: List[Dict[str, Any]]
    publishable_attributes: List[str]
    restricted_attributes: List[str]
    summary_reason: str
    metadata: Dict[str, Any] = dc.field(default_factory=dict)

    @property
    def has_conflicts(self) -> bool:
        return len(self.unresolved_conflicts) > 0

    @property
    def review_item_count(self) -> int:
        return len(self.review_queue)

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "overall_trust_status": self.overall_trust_status.value,
            "overall_publishability": self.overall_publishability.value,
            "trust_score": round(self.trust_score, 4),
            "trust_score_formula": self.trust_score_formula,
            "trust_score_breakdown": {k: round(v, 4) for k, v in self.trust_score_breakdown.items()},
            "attribute_trust": {k: v.to_dict() for k, v in self.attribute_trust.items()},
            "claim_trust": [c.to_dict() for c in self.claim_trust],
            "review_queue": [r.to_dict() for r in self.review_queue],
            "unresolved_conflicts": self.unresolved_conflicts,
            "publishable_attributes": self.publishable_attributes,
            "restricted_attributes": self.restricted_attributes,
            "summary_reason": self.summary_reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProductTrustReport:
        return cls(
            product_id=data["product_id"],
            manufacturer=data["manufacturer"],
            model=data["model"],
            overall_trust_status=TrustStatus(data["overall_trust_status"]),
            overall_publishability=PublishabilityStatus(data["overall_publishability"]),
            trust_score=float(data["trust_score"]),
            trust_score_formula=data["trust_score_formula"],
            trust_score_breakdown=data.get("trust_score_breakdown", {}),
            attribute_trust={k: AttributeTrustResult.from_dict(v) for k, v in data.get("attribute_trust", {}).items()},
            claim_trust=[ClaimTrustResult.from_dict(c) for c in data.get("claim_trust", [])],
            review_queue=[ReviewItem.from_dict(r) for r in data.get("review_queue", [])],
            unresolved_conflicts=data.get("unresolved_conflicts", []),
            publishable_attributes=data.get("publishable_attributes", []),
            restricted_attributes=data.get("restricted_attributes", []),
            summary_reason=data.get("summary_reason", ""),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Batch Trust Report
# ---------------------------------------------------------------------------

@dc.dataclass
class BatchTrustReport:
    """
    Summary report across all evaluated products in the dataset.
    """
    total_products: int
    trusted_count: int
    review_required_count: int
    conflicted_count: int
    publishable_count: int
    publishable_with_warning_count: int
    not_publishable_count: int
    avg_trust_score: float
    total_review_items: int
    products: List[Dict[str, Any]]
    generated_at: str = dc.field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "total_products": self.total_products,
            "trusted_count": self.trusted_count,
            "review_required_count": self.review_required_count,
            "conflicted_count": self.conflicted_count,
            "publishable_count": self.publishable_count,
            "publishable_with_warning_count": self.publishable_with_warning_count,
            "not_publishable_count": self.not_publishable_count,
            "avg_trust_score": round(self.avg_trust_score, 4),
            "total_review_items": self.total_review_items,
            "products": self.products,
            "generated_at": self.generated_at,
        }
