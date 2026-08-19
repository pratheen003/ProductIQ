"""
ProductIQ Validation Models — Phase 3
======================================
Data structures representing the output of the validation engine.

Every ValidationFinding records:
  - WHAT was checked (rule ID, field, description)
  - WHAT values were observed (actual values, units, sources)
  - WHY it passed/failed/conflicted (explanation)
  - WHICH evidence it references (provenance links)

Design principles:
  - No LLM calls. All validation is deterministic rule-based logic.
  - No fabricated values. Validation only reads, never invents.
  - Conflicts are explicit — never silently resolved.
  - Every finding is independently serializable to JSON.
  - Phase 2 provenance is fully preserved through validation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Validation status — result tier for each check
# ---------------------------------------------------------------------------

class ValidationStatus(str, Enum):
    """Result tier for a single validation finding."""
    PASS        = "PASS"         # Check passed — no issues found
    WARNING     = "WARNING"      # Minor issue — product is usable but attention needed
    CONFLICT    = "CONFLICT"     # Two sources disagree after normalization
    FAIL        = "FAIL"         # Check failed — serious issue detected
    NOT_CHECKED = "NOT_CHECKED"  # Check was skipped due to missing data


# ---------------------------------------------------------------------------
# Validation severity — impact level
# ---------------------------------------------------------------------------

class ValidationSeverity(str, Enum):
    """Impact level of a validation finding."""
    INFO     = "INFO"     # Informational — no action needed
    LOW      = "LOW"      # Low impact — worth noting
    MEDIUM   = "MEDIUM"   # Medium impact — should be reviewed
    HIGH     = "HIGH"     # High impact — needs resolution before use
    CRITICAL = "CRITICAL" # Critical — product intelligence is unreliable


# ---------------------------------------------------------------------------
# Validation category — which category of rule fired
# ---------------------------------------------------------------------------

class ValidationCategory(str, Enum):
    """Category of validation rule."""
    SCHEMA          = "SCHEMA"          # A. Schema conformance
    REQUIRED_FIELD  = "REQUIRED_FIELD"  # B. Required field presence
    TYPE            = "TYPE"            # C. Type correctness
    RANGE           = "RANGE"           # D. Range / plausibility
    UNIT            = "UNIT"            # E. Unit / canonical consistency
    CONSISTENCY     = "CONSISTENCY"     # F. Cross-source consistency
    ENGINEERING     = "ENGINEERING"     # G. Engineering relationship plausibility
    MISSING_DATA    = "MISSING_DATA"    # H. Missing data completeness
    CONFLICT        = "CONFLICT"        # I. Detected evidence conflict


# ---------------------------------------------------------------------------
# Evidence reference used in findings (mirrors normalization EvidenceRef)
# ---------------------------------------------------------------------------

@dataclass
class FindingEvidenceRef:
    """Lightweight provenance reference within a ValidationFinding."""
    source_id:   str
    source_type: str       # "pdf" | "csv" | "web"
    attribute:   str       # original evidence attribute name
    raw_value:   str       # exact string from source
    raw_unit:    Optional[str] = None
    page:        Optional[int] = None
    row:         Optional[int] = None
    column:      Optional[str] = None
    section:     Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Core validation finding — single check result
# ---------------------------------------------------------------------------

@dataclass
class ValidationFinding:
    """
    Result of applying one validation rule to one product field.

    Must contain enough information for a dashboard to display:
      - rule_id + description → what was checked
      - status + severity     → how serious it is
      - field + category      → where it applies
      - actual_value + expected_condition → what was found vs expected
      - explanation           → human-readable reason
      - evidence_refs         → which evidence supports this finding
    """
    rule_id:    str                   # e.g. "RANGE_RATED_POWER_POSITIVE"
    category:   ValidationCategory   # Schema / Range / Conflict / Engineering / etc.
    status:     ValidationStatus     # PASS / WARNING / CONFLICT / FAIL / NOT_CHECKED
    severity:   ValidationSeverity   # INFO / LOW / MEDIUM / HIGH / CRITICAL

    # What was checked
    field:              str           # Canonical field name (e.g. "rated_current")
    description:        str           # Short human-readable rule description

    # What was found
    actual_value:       Optional[Any] = None   # Value that was checked
    actual_unit:        Optional[str] = None   # Unit of actual_value
    expected_condition: Optional[str] = None   # Expected condition (e.g. "> 0")

    # Why it passed/failed
    explanation:        str = ""      # Full human-readable explanation

    # Which evidence references this finding
    evidence_refs:      List[FindingEvidenceRef] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def __str__(self) -> str:
        return (
            f"[{self.status.value}/{self.severity.value}] "
            f"{self.rule_id}: {self.explanation}"
        )


# ---------------------------------------------------------------------------
# Product validation report — all findings for one product
# ---------------------------------------------------------------------------

@dataclass
class ProductValidationReport:
    """
    Complete validation result for a single motor product.

    Contains:
      - Summary statistics (pass/warn/conflict/fail counts)
      - All ValidationFinding instances (one per rule applied)
      - Validation metadata (version, timestamp, product info)
    """
    product_id:   str
    manufacturer: str
    model:        str

    findings:     List[ValidationFinding] = field(default_factory=list)

    # Overall result (worst status across all findings)
    overall_status: ValidationStatus = ValidationStatus.PASS

    # Metadata
    validation_version: str = "3.0.0"
    validation_notes:   List[str] = field(default_factory=list)

    # ---------------------------------------------------------------------------
    # Computed summary properties
    # ---------------------------------------------------------------------------

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.status == ValidationStatus.PASS)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.status == ValidationStatus.WARNING)

    @property
    def conflict_count(self) -> int:
        return sum(1 for f in self.findings if f.status == ValidationStatus.CONFLICT)

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.findings if f.status == ValidationStatus.FAIL)

    @property
    def not_checked_count(self) -> int:
        return sum(1 for f in self.findings if f.status == ValidationStatus.NOT_CHECKED)

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def has_conflicts(self) -> bool:
        return self.conflict_count > 0

    @property
    def has_failures(self) -> bool:
        return self.fail_count > 0

    @property
    def findings_by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self.findings:
            counts[f.category.value] = counts.get(f.category.value, 0) + 1
        return counts

    def compute_overall_status(self) -> ValidationStatus:
        """Derive overall status from the worst finding status."""
        if any(f.status == ValidationStatus.FAIL for f in self.findings):
            return ValidationStatus.FAIL
        if any(f.status == ValidationStatus.CONFLICT for f in self.findings):
            return ValidationStatus.CONFLICT
        if any(f.status == ValidationStatus.WARNING for f in self.findings):
            return ValidationStatus.WARNING
        return ValidationStatus.PASS

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "validation_version": self.validation_version,
            "validation_notes": self.validation_notes,
            "overall_status": self.overall_status.value,
            "summary": {
                "total_findings": self.total_findings,
                "pass":           self.pass_count,
                "warning":        self.warning_count,
                "conflict":       self.conflict_count,
                "fail":           self.fail_count,
                "not_checked":    self.not_checked_count,
                "by_category":    self.findings_by_category,
            },
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Batch validation report — summary across all products
# ---------------------------------------------------------------------------

@dataclass
class BatchValidationReport:
    """Summary statistics for a complete batch validation run."""
    products_processed:  int = 0
    products_passing:    int = 0
    products_with_warn:  int = 0
    products_with_conflict: int = 0
    products_failing:    int = 0
    total_findings:      int = 0
    findings_pass:       int = 0
    findings_warning:    int = 0
    findings_conflict:   int = 0
    findings_fail:       int = 0
    findings_not_checked: int = 0
    findings_by_category: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
