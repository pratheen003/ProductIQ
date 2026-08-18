"""
ProductIQ Extraction Models
============================
Phase 1 raw evidence layer.

This module defines the raw extraction data model that sits UPSTREAM of the
canonical MotorProduct schema. Raw evidence records preserve exactly what the
source says — nothing more, nothing less.

Separation of concerns:
    RAW SOURCE → EvidenceRecord (Phase 1)
               → Phase 2 normalises → FieldValue / MotorProduct (frozen Phase 0 schema)

Rules:
- An EvidenceRecord never invents values not present in the source.
- An EvidenceRecord never converts units (that is Phase 2).
- An EvidenceRecord never resolves conflicts (that is Phase 3).
- Every EvidenceRecord must carry enough provenance for a reviewer to find
  the original value in the original source without any additional context.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Extraction status — whether the source was successfully processed
# ---------------------------------------------------------------------------

class ExtractionStatus(str, Enum):
    """Overall status of an extraction attempt for a single source."""
    SUCCESS = "success"
    PARTIAL = "partial"       # Some evidence retrieved but with errors
    FAILED  = "failed"        # No evidence retrieved; error recorded


class ExtractionMethod(str, Enum):
    """How the value was located within the source."""
    TABLE      = "table"       # Extracted from a structured table
    TEXT       = "text"        # Extracted from free-running text (regex)
    COLUMN     = "column"      # CSV column lookup
    HTML_TABLE = "html_table"  # HTML <table> element
    HTML_DL    = "html_dl"     # HTML <dl>/<dt>/<dd> definition list
    HTML_TEXT  = "html_text"   # HTML free text / paragraph
    HEADER     = "header"      # Extracted from a table header / column header
    UNKNOWN    = "unknown"


# ---------------------------------------------------------------------------
# Evidence Record — one extracted fact from one source location
# ---------------------------------------------------------------------------

@dataclass
class EvidenceRecord:
    """
    A single raw extracted fact, fully traceable to its origin.

    Provenance fields:
        source_id    — stable identifier for the source document
        source_type  — "pdf" | "web" | "csv"
        product_id   — ProductIQ product ID (from manifest)
        page         — PDF page number (1-indexed); None for non-PDF
        row          — CSV row number (1-indexed, header excluded); None for non-CSV
        column       — CSV column name; None for non-CSV
        url          — Web page URL; None for non-web
        section      — Heading or section context (web/PDF); None if unavailable

    Value fields:
        attribute    — ProductIQ field name (e.g. "rated_power") or raw column name
        raw_value    — Exact string as it appeared in the source
        value        — Parsed numeric value (float) if applicable; None otherwise
        unit         — Unit string explicitly found in source; None if not stated
        evidence_text — Surrounding text/row context for traceability

    Quality fields:
        method       — How the value was found (ExtractionMethod)
        confidence   — Extraction confidence 0.0–1.0
    """
    # Identity
    source_id:    str
    source_type:  str                  # "pdf" | "web" | "csv"
    product_id:   str

    # Provenance (source-type-specific)
    page:         Optional[int]   = None   # PDF only
    row:          Optional[int]   = None   # CSV only
    column:       Optional[str]   = None   # CSV only
    url:          Optional[str]   = None   # Web only
    section:      Optional[str]   = None   # PDF heading / Web section heading

    # Extracted content
    attribute:    str             = ""
    raw_value:    str             = ""
    value:        Optional[float] = None
    unit:         Optional[str]   = None
    evidence_text: str            = ""

    # Quality
    method:       str             = ExtractionMethod.UNKNOWN.value
    confidence:   float           = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EvidenceRecord":
        return cls(**d)


# ---------------------------------------------------------------------------
# Extraction Result — outcome of processing one source for one product
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """
    The complete result of extracting one source (PDF/CSV/web) for one product.

    Contains:
      - status: did extraction succeed?
      - evidence: list of raw EvidenceRecord items (may be empty on failure)
      - error: error description if status != SUCCESS
      - metadata: source reference info for logging and summary
    """
    source_id:    str
    source_type:  str
    product_id:   str
    status:       str                    # ExtractionStatus value
    evidence:     List[EvidenceRecord]   = field(default_factory=list)
    error:        Optional[str]          = None
    source_ref:   Optional[str]          = None   # file path or URL
    pages_read:   Optional[int]          = None   # PDF: pages scanned
    rows_read:    Optional[int]          = None   # CSV: rows scanned

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def succeeded(self) -> bool:
        return self.status == ExtractionStatus.SUCCESS.value

    def to_dict(self) -> dict:
        d = asdict(self)
        # evidence list is already converted by asdict
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def failure(
        cls,
        source_id: str,
        source_type: str,
        product_id: str,
        error: str,
        source_ref: Optional[str] = None,
    ) -> "ExtractionResult":
        """Factory for a failed extraction result — no evidence, error recorded."""
        return cls(
            source_id=source_id,
            source_type=source_type,
            product_id=product_id,
            status=ExtractionStatus.FAILED.value,
            evidence=[],
            error=error,
            source_ref=source_ref,
        )


# ---------------------------------------------------------------------------
# Batch Extraction Summary
# ---------------------------------------------------------------------------

@dataclass
class BatchExtractionSummary:
    """Summary statistics for a full batch extraction run."""
    products_discovered: int = 0
    pdf_attempted:  int = 0
    pdf_succeeded:  int = 0
    pdf_failed:     int = 0
    csv_attempted:  int = 0
    csv_succeeded:  int = 0
    csv_failed:     int = 0
    web_attempted:  int = 0
    web_succeeded:  int = 0
    web_failed:     int = 0
    total_evidence: int = 0

    def to_dict(self) -> dict:
        return asdict(self)
