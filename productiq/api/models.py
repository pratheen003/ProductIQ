"""
ProductIQ API Data Transfer Objects (DTOs) — Phase 6
=====================================================
Pydantic schemas for clean REST API responses and requests.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SpecificationDTO(BaseModel):
    field: str
    canonical_value: Optional[Any] = None
    canonical_unit: Optional[str] = None
    trust_status: str                      # TRUSTED, CONFLICTED, UNVERIFIED, UNSUPPORTED, MISSING, REVIEW_REQUIRED
    publishability: str                    # PUBLISHABLE, PUBLISHABLE_WITH_WARNING, REVIEW_REQUIRED, NOT_PUBLISHABLE
    validation_status: Optional[str] = None # PASS, WARNING, CONFLICT, FAIL, NOT_CHECKED
    is_conflicted: bool = False
    evidence_sources: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0
    reason: str = ""
    validation_rule_ids: List[str] = Field(default_factory=list)


class ClaimDTO(BaseModel):
    claim_text: str
    category: str
    claim_type: str                        # SOURCE_BACKED, INFERRED, UNSUPPORTED
    trust_status: str                      # TRUSTED, REVIEW_REQUIRED, CONFLICTED, UNVERIFIED, etc.
    publishability: str                    # PUBLISHABLE, PUBLISHABLE_WITH_WARNING, REVIEW_REQUIRED, NOT_PUBLISHABLE
    supporting_fields: List[str] = Field(default_factory=list)
    evidence_sources: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    reason: str = ""


class ConflictSourceDTO(BaseModel):
    source_id: str = ""
    source_type: str = "pdf"               # pdf, csv, web, manual
    source_name: str = ""                  # Human readable name
    value: Optional[Any] = None
    unit: Optional[str] = None
    raw_value: Optional[str] = None
    location: Optional[str] = None         # Page number, Row number, Section
    confidence: Optional[float] = 1.0


class ConflictRecordDTO(BaseModel):
    field: str
    canonical_field: str = ""
    description: str = ""
    action_needed: str = ""
    recommended_action: str = ""
    sources: List[ConflictSourceDTO] = Field(default_factory=list)
    conflicting_values: Optional[List[Dict[str, Any]]] = None


class ReviewItemDTO(BaseModel):
    review_id: str
    product_id: str = ""
    target_type: str                       # attribute, claim, validation
    target_name: str
    severity: str                          # CRITICAL, HIGH, MEDIUM, LOW
    issue_type: str                        # CONFLICT, WARNING, FAIL, UNVERIFIED_INFERENCE, MISSING_DATA
    description: str
    conflicting_values: Optional[List[Dict[str, Any]]] = None
    conflicting_sources: List[ConflictSourceDTO] = Field(default_factory=list)
    validation_rule_id: Optional[str] = None
    affected_claims: List[str] = Field(default_factory=list)
    recommended_action: str = ""
    status: str = "OPEN"                   # OPEN, RESOLVED, DISMISSED
    resolution_note: Optional[str] = None
    resolved_value: Optional[Any] = None
    resolved_by: Optional[str] = None


class EvidenceRecordDTO(BaseModel):
    source_id: str
    source_type: str                       # pdf, csv, web, llm-enrichment
    product_id: str
    attribute: str
    raw_value: str
    raw_unit: Optional[str] = None
    parsed_value: Optional[Any] = None
    method: str = ""
    confidence: float = 1.0
    page: Optional[int] = None
    row: Optional[int] = None
    column: Optional[str] = None
    url: Optional[str] = None
    section: Optional[str] = None
    evidence_text: Optional[str] = None


class ProductSummaryDTO(BaseModel):
    product_id: str
    manufacturer: str
    model: str
    category: str = "Industrial Electric Motor"
    trust_score: float
    overall_trust_status: str              # TRUSTED, CONFLICTED, REVIEW_REQUIRED, etc.
    overall_publishability: str            # PUBLISHABLE, PUBLISHABLE_WITH_WARNING, REVIEW_REQUIRED, NOT_PUBLISHABLE
    review_items_count: int
    conflicts_count: int
    publishable_attributes_count: int
    restricted_attributes_count: int
    rated_power_kw: Optional[float] = None
    rated_voltage_v: Optional[float] = None
    rated_speed_rpm: Optional[float] = None
    poles: Optional[int] = None
    frame_size: Optional[str] = None
    summary_reason: str = ""


class ProductDetailDTO(BaseModel):
    product_id: str
    manufacturer: str
    model: str
    category: str = "Industrial Electric Motor"
    trust_score: float
    trust_score_formula: str
    trust_score_breakdown: Dict[str, float]
    overall_trust_status: str
    overall_publishability: str
    summary_reason: str
    specifications: Dict[str, SpecificationDTO]
    claims: List[ClaimDTO] = Field(default_factory=list)
    review_queue: List[ReviewItemDTO] = Field(default_factory=list)
    unresolved_conflicts: List[ConflictRecordDTO] = Field(default_factory=list)
    publishable_attributes: List[str] = Field(default_factory=list)
    restricted_attributes: List[str] = Field(default_factory=list)
    evidence_records: List[EvidenceRecordDTO] = Field(default_factory=list)
    commercial_summary: str = ""
    technical_description: str = ""
    target_applications: List[str] = Field(default_factory=list)
    search_keywords: List[str] = Field(default_factory=list)


class BatchSummaryDTO(BaseModel):
    total_products: int
    trusted_count: int
    review_required_count: int
    conflicted_count: int
    publishable_count: int
    publishable_with_warning_count: int
    not_publishable_count: int
    avg_trust_score: float
    total_review_items: int
    trust_distribution: Dict[str, int]
    publishability_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    products: List[ProductSummaryDTO]
    generated_at: str


class ReviewResolutionRequestDTO(BaseModel):
    selected_source: Optional[str] = None  # e.g., "pdf", "csv", "manual"
    resolved_value: Any
    resolution_note: str
    reviewer: str = "Domain Engineer"


class ReviewResolutionResponseDTO(BaseModel):
    success: bool
    review_id: str
    product_id: str
    status: str
    resolved_value: Any
    message: str


class IngestStatusDTO(BaseModel):
    pipeline_id: str
    current_stage: str
    status: str                            # RUNNING, COMPLETE, FAILED
    stages: List[Dict[str, Any]]
    total_records_extracted: int
    products_discovered: int
