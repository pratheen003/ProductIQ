"""
ProductIQ Normalization Models — Phase 2
=========================================
Data structures representing the output of normalization:
  - NormalizedField: a single canonical field after normalization
  - ConflictRecord: two evidence values that disagree after normalization
  - NormalizationIssue: a parsing/conversion failure record
  - NormalizedProduct: the full normalized motor product (Phase 2 output)
  - NormalizationReport: batch normalization summary statistics

Design principles:
  - Every NormalizedField preserves raw_value, raw_unit, canonical_value,
    canonical_unit, AND the list of contributing EvidenceRecord references.
  - Conflicts are preserved verbatim — never silently resolved.
  - Malformed inputs produce a NormalizationIssue, not a fabricated value.
  - No LLM calls. All conversions are deterministic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Normalization outcome for a single evidence-to-field conversion attempt
# ---------------------------------------------------------------------------

class NormalizationOutcome(str, Enum):
    """Outcome of a single field normalization attempt."""
    NORMALIZED   = "normalized"    # Successfully converted to canonical unit
    PASSTHROUGH  = "passthrough"   # Already in canonical unit — no conversion needed
    CONFLICT     = "conflict"      # Multiple evidence values disagree after normalization
    MISSING      = "missing"       # No evidence available for this field
    PARSE_ERROR  = "parse_error"   # Could not parse raw value
    UNKNOWN_UNIT = "unknown_unit"  # Unit present but not recognized/convertible
    UNMAPPED     = "unmapped"      # Evidence attribute not mapped to a canonical field


# ---------------------------------------------------------------------------
# Evidence reference — lightweight provenance pointer
# ---------------------------------------------------------------------------

@dataclass
class EvidenceRef:
    """
    Lightweight pointer back to the original EvidenceRecord.
    Carries enough provenance for full traceability without duplicating
    the entire EvidenceRecord into every normalized output.
    """
    source_id:    str
    source_type:  str              # "pdf" | "csv" | "web"
    product_id:   str
    attribute:    str              # original evidence attribute name
    raw_value:    str              # exact string from source
    raw_unit:     Optional[str]    # unit as found in source (may differ from canonical)
    parsed_value: Optional[float]  # numeric value parsed from raw_value
    method:       str              # extraction method (table, column, etc.)
    confidence:   float            # extraction confidence [0.0, 1.0]

    # Source-type-specific provenance
    page:   Optional[int]  = None  # PDF page number
    row:    Optional[int]  = None  # CSV row number
    column: Optional[str]  = None  # CSV column name
    url:    Optional[str]  = None  # Web URL
    section: Optional[str] = None  # Section heading

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EvidenceRef":
        return cls(**d)


# ---------------------------------------------------------------------------
# Conflict record — two evidence values that disagree
# ---------------------------------------------------------------------------

@dataclass
class ConflictRecord:
    """
    Records that two evidence observations for the same canonical field
    produced different normalized values. Phase 3 is responsible for
    resolving this conflict. Phase 2 only surfaces it.
    """
    canonical_field: str           # e.g. "rated_current"
    value_a: Optional[float]       # First normalized value
    unit_a:  Optional[str]         # Canonical unit for value_a
    source_a: EvidenceRef          # Provenance of value_a

    value_b: Optional[float]       # Second normalized value (conflicts with value_a)
    unit_b:  Optional[str]         # Canonical unit for value_b
    source_b: EvidenceRef          # Provenance of value_b

    note: str = ""                 # Human-readable description

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Normalization issue — parse failure or unknown unit
# ---------------------------------------------------------------------------

@dataclass
class NormalizationIssue:
    """
    Records a normalization failure without fabricating a value.
    A NormalizationIssue is raised whenever a raw value cannot be safely
    parsed or converted — it is never silently swallowed.
    """
    canonical_field: str           # Target canonical field (or "unmapped")
    evidence_attribute: str        # Original evidence attribute name
    raw_value:   str               # Raw string that could not be processed
    raw_unit:    Optional[str]     # Unit that was found (if any)
    outcome:     NormalizationOutcome
    reason:      str               # Human-readable failure description
    source_ref:  Optional[EvidenceRef] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Normalized field — a single canonical field after normalization
# ---------------------------------------------------------------------------

@dataclass
class NormalizedField:
    """
    The result of normalizing all evidence for a single canonical field.

    Preservation guarantees:
    - raw_value and raw_unit from EVERY contributing evidence record are
      accessible via evidence_refs.
    - canonical_value and canonical_unit are the normalized representation.
    - If multiple sources agree: all evidence_refs preserved, single value.
    - If multiple sources conflict: canonical_value=None, conflicts populated.
    - If no evidence: outcome=MISSING, all value fields None.
    """
    canonical_field: str              # MotorProduct field name (e.g. "rated_power")
    canonical_unit:  Optional[str]    # From CANONICAL_UNITS (e.g. "kW")
    canonical_value: Optional[Any]    # Normalized value (float or str); None if missing/conflict
    outcome:         NormalizationOutcome

    # All contributing evidence references (raw values preserved here)
    evidence_refs:   List[EvidenceRef] = field(default_factory=list)
    conflicts:       List[ConflictRecord] = field(default_factory=list)

    # Aggregated confidence across all evidence
    confidence:  Optional[float]  = None
    notes:       List[str]        = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizedField":
        """Deserialize from dict (used for loading saved output)."""
        evidence_refs = [EvidenceRef(**r) for r in d.get("evidence_refs", [])]
        conflicts = [ConflictRecord(
            canonical_field=c["canonical_field"],
            value_a=c["value_a"], unit_a=c["unit_a"],
            source_a=EvidenceRef(**c["source_a"]),
            value_b=c["value_b"], unit_b=c["unit_b"],
            source_b=EvidenceRef(**c["source_b"]),
            note=c.get("note", "")
        ) for c in d.get("conflicts", [])]
        return cls(
            canonical_field=d["canonical_field"],
            canonical_unit=d.get("canonical_unit"),
            canonical_value=d.get("canonical_value"),
            outcome=NormalizationOutcome(d["outcome"]),
            evidence_refs=evidence_refs,
            conflicts=conflicts,
            confidence=d.get("confidence"),
            notes=d.get("notes", []),
        )


# ---------------------------------------------------------------------------
# Normalized product — Phase 2 output for one motor
# ---------------------------------------------------------------------------

@dataclass
class NormalizedProduct:
    """
    Complete normalized representation of a single motor product.

    This is Phase 2's output artifact:
      - Identity fields from the manifest
      - Canonical fields from normalization
      - Unmapped evidence attributes (nothing silently dropped)
      - Normalization issues (parse failures, unknown units)
      - Metadata (normalization timestamp, version)
    """
    product_id:   str
    manufacturer: str
    model:        str
    product_type: str = "three_phase_induction_motor"

    # Canonical field results (keyed by field name)
    fields: Dict[str, NormalizedField] = field(default_factory=dict)

    # Evidence attributes that have no canonical field mapping
    unmapped_evidence: List[EvidenceRef] = field(default_factory=list)

    # Normalization issues (parse errors, unknown units)
    issues: List[NormalizationIssue] = field(default_factory=list)

    # Metadata
    normalization_version: str = "2.0.0"
    normalization_notes:   List[str] = field(default_factory=list)

    # --- Convenience properties ---

    @property
    def field_count(self) -> int:
        return len(self.fields)

    @property
    def normalized_count(self) -> int:
        """Fields with a concrete normalized value."""
        return sum(
            1 for f in self.fields.values()
            if f.outcome in (NormalizationOutcome.NORMALIZED, NormalizationOutcome.PASSTHROUGH)
            and f.canonical_value is not None
        )

    @property
    def conflict_count(self) -> int:
        return sum(1 for f in self.fields.values() if f.conflicts)

    @property
    def missing_count(self) -> int:
        return sum(1 for f in self.fields.values() if f.outcome == NormalizationOutcome.MISSING)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "product_type": self.product_type,
            "normalization_version": self.normalization_version,
            "normalization_notes": self.normalization_notes,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "unmapped_evidence": [e.to_dict() for e in self.unmapped_evidence],
            "issues": [i.to_dict() for i in self.issues],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @property
    def summary(self) -> dict:
        return {
            "product_id": self.product_id,
            "fields_total": self.field_count,
            "fields_normalized": self.normalized_count,
            "fields_conflicted": self.conflict_count,
            "fields_missing": self.missing_count,
            "unmapped_evidence": len(self.unmapped_evidence),
            "issues": self.issue_count,
        }


# ---------------------------------------------------------------------------
# Batch normalization report
# ---------------------------------------------------------------------------

@dataclass
class NormalizationReport:
    """Summary statistics for a complete batch normalization run."""
    products_processed: int = 0
    products_succeeded: int = 0
    products_failed:    int = 0
    evidence_consumed:  int = 0
    fields_normalized:  int = 0
    fields_conflicted:  int = 0
    fields_missing:     int = 0
    unmapped_attrs:     int = 0
    parse_errors:       int = 0
    unknown_units:      int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
