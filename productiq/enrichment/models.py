"""
ProductIQ Enrichment Models — Phase 4
=====================================
Structured data representations for AI-enriched product intelligence.

Design commitments:
- Strict schema enforcement: every claim is typed and categorized.
- Anti-hallucination tracking: clear distinction between source_backed_claims and inferred_claims.
- Unresolved conflicts are surfaced verbatim and never suppressed.
- Full evidence provenance is preserved through to commercial output.
"""
from __future__ import annotations

import dataclasses as dc
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dc.dataclass
class EnrichmentClaim:
    """An individual structured claim made in the enrichment output."""
    claim_text: str
    category: str               # "performance", "mechanical", "electrical", "application", "standard"
    field: Optional[str] = None # associated canonical field name if applicable
    is_source_backed: bool = False
    evidence_sources: List[str] = dc.field(default_factory=list) # e.g. ["pdf:p.5", "csv:col_rated_speed"]
    confidence: float = 1.0     # 0.0 to 1.0
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return dc.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> EnrichmentClaim:
        return cls(
            claim_text=data["claim_text"],
            category=data.get("category", "specification"),
            field=data.get("field"),
            is_source_backed=data.get("is_source_backed", False),
            evidence_sources=data.get("evidence_sources", []),
            confidence=float(data.get("confidence", 1.0)),
            notes=data.get("notes"),
        )


@dc.dataclass
class ProductEnrichment:
    """
    Complete AI enrichment output for a single motor product.
    Grounded in Phase 2 normalization and Phase 3 validation reports.
    """
    product_id: str
    manufacturer: str
    model: str                                  # Motor model name (e.g. W22 Severe Process)

    # Core AI-generated commercial content
    summary: str                                # 2-3 sentence commercial overview
    technical_description: str                  # Comprehensive engineering description
    key_selling_points: List[str] = dc.field(default_factory=list)
    target_applications: List[str] = dc.field(default_factory=list)
    suggested_keywords: List[str] = dc.field(default_factory=list)

    # Inferred parameters (explicitly marked DataStatus.INFERRED)
    inferred_fields: Dict[str, Any] = dc.field(default_factory=dict)

    # Claim audit trail
    source_backed_claims: List[EnrichmentClaim] = dc.field(default_factory=list)
    inferred_claims: List[EnrichmentClaim] = dc.field(default_factory=list)

    # Conflict & integrity preservation
    unresolved_conflicts: List[Dict[str, Any]] = dc.field(default_factory=list)
    missing_information_notes: List[str] = dc.field(default_factory=list)
    enrichment_warnings: List[str] = dc.field(default_factory=list)

    # Execution metadata
    provider: str = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    prompt_version: str = "4.0.0"
    generated_at: str = dc.field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_claims(self) -> int:
        return len(self.source_backed_claims) + len(self.inferred_claims)

    @property
    def has_conflicts(self) -> bool:
        return len(self.unresolved_conflicts) > 0

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "summary": self.summary,
            "technical_description": self.technical_description,
            "key_selling_points": self.key_selling_points,
            "target_applications": self.target_applications,
            "suggested_keywords": self.suggested_keywords,
            "inferred_fields": self.inferred_fields,
            "source_backed_claims": [c.to_dict() for c in self.source_backed_claims],
            "inferred_claims": [c.to_dict() for c in self.inferred_claims],
            "unresolved_conflicts": self.unresolved_conflicts,
            "missing_information_notes": self.missing_information_notes,
            "enrichment_warnings": self.enrichment_warnings,
            "metadata": {
                "provider": self.provider,
                "llm_model": self.llm_model,
                "prompt_version": self.prompt_version,
                "generated_at": self.generated_at,
                "total_claims": self.total_claims,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> ProductEnrichment:
        meta = data.get("metadata", {})
        return cls(
            product_id=data["product_id"],
            manufacturer=data["manufacturer"],
            model=data["model"],
            summary=data.get("summary", ""),
            technical_description=data.get("technical_description", ""),
            key_selling_points=data.get("key_selling_points", []),
            target_applications=data.get("target_applications", []),
            suggested_keywords=data.get("suggested_keywords", []),
            inferred_fields=data.get("inferred_fields", {}),
            source_backed_claims=[EnrichmentClaim.from_dict(c) for c in data.get("source_backed_claims", [])],
            inferred_claims=[EnrichmentClaim.from_dict(c) for c in data.get("inferred_claims", [])],
            unresolved_conflicts=data.get("unresolved_conflicts", []),
            missing_information_notes=data.get("missing_information_notes", []),
            enrichment_warnings=data.get("enrichment_warnings", []),
            provider=meta.get("provider", data.get("provider", "groq")),
            llm_model=meta.get("llm_model", meta.get("model", data.get("llm_model", "unknown"))),
            prompt_version=meta.get("prompt_version", data.get("prompt_version", "4.0.0")),
            generated_at=meta.get("generated_at", data.get("generated_at", "")),
        )


@dc.dataclass
class BatchEnrichmentReport:
    """Summary of batch enrichment run across the dataset."""
    products_processed: int = 0
    products_enriched: int = 0
    products_failed: int = 0
    total_claims_generated: int = 0
    source_backed_claims_count: int = 0
    inferred_claims_count: int = 0
    unresolved_conflicts_count: int = 0
    provider: str = "groq"
    model: str = ""
    timestamp: str = dc.field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return dc.asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
