"""
ProductIQ Catalog Schema — Strongly-Typed Domain Models for Unilog Pipeline
===========================================================================
Defines the scoped schema, nested field containers, 4-tier trust statuses,
and input/output data representations.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class CatalogTrustStatus(str, Enum):
    """
    Four-tier trust status redefined specifically for the Unilog Catalog Domain:
    - VERIFIED: Exact match against approved lookup list (LOV / manufacturer list) or directly present in clean input.
    - INFERRED: Value derived via fuzzy match, regex pattern extraction from Part_Desc, or formula synthesis below exact-match threshold.
    - CONFLICTED: Conflicting input brand signals (E1_Brand vs DIB_Brand vs Part_Manuf vs Part_Desc) after placeholder filtering.
    - UNKNOWN: No derivable value from inputs or lookup tables.
    """
    VERIFIED = "Verified"
    INFERRED = "Inferred"
    CONFLICTED = "Conflicted"
    UNKNOWN = "Unknown"


class CatalogField(BaseModel, Generic[T]):
    """
    Nested field container preserving value, status, confidence, sources, and reason.
    """
    value: Optional[T] = None
    status: CatalogTrustStatus = CatalogTrustStatus.UNKNOWN
    confidence: float = 1.0
    sources: List[str] = Field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "status": self.status.value if isinstance(self.status, CatalogTrustStatus) else str(self.status),
            "confidence": round(self.confidence, 4),
            "sources": self.sources,
            "reason": self.reason,
        }


class CatalogAttributeTriple(BaseModel):
    """
    Represents an attribute triple: (LABEL, VALUE, UOM) with canonicalization & trust metadata.
    """
    label: str
    value: Any
    uom: Optional[str] = None
    raw_value: Optional[str] = None
    raw_uom: Optional[str] = None
    status: CatalogTrustStatus = CatalogTrustStatus.UNKNOWN
    confidence: float = 1.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "uom": self.uom,
            "raw_value": self.raw_value,
            "raw_uom": self.raw_uom,
            "status": self.status.value if isinstance(self.status, CatalogTrustStatus) else str(self.status),
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
        }


class CatalogInputRow(BaseModel):
    """
    Raw input row matching Unihack__Sample_Dataset_-_Input.csv structure.
    """
    row_id: int
    mfg_part_num: str
    part_desc: str
    e1_brand: Optional[str] = None
    unilog_brand: Optional[str] = None
    dib_brand: Optional[str] = None
    part_manuf: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "mfg_part_num": self.mfg_part_num,
            "part_desc": self.part_desc,
            "e1_brand": self.e1_brand,
            "unilog_brand": self.unilog_brand,
            "dib_brand": self.dib_brand,
            "part_manuf": self.part_manuf,
        }


class CatalogProduct(BaseModel):
    """
    Enriched, normalized, trust-evaluated catalog item with scoped schema fields.
    """
    row_id: int
    mfg_part_num: str
    part_desc: str
    raw_input: CatalogInputRow

    # Scoped Canonical Enriched Fields
    manufacturer_name: CatalogField[str] = Field(default_factory=lambda: CatalogField[str]())
    brand_name: CatalogField[str] = Field(default_factory=lambda: CatalogField[str]())
    trade_name: CatalogField[str] = Field(default_factory=lambda: CatalogField[str]())
    manufacturer_part_number: CatalogField[str] = Field(default_factory=lambda: CatalogField[str]())
    product_name: CatalogField[str] = Field(default_factory=lambda: CatalogField[str]())
    series: CatalogField[str] = Field(default_factory=lambda: CatalogField[str]())
    classpath: CatalogField[str] = Field(default_factory=lambda: CatalogField[str]())

    # Normalized Attribute Triples
    attributes: List[CatalogAttributeTriple] = Field(default_factory=list)

    # Scoped Descriptions
    short_desc: CatalogField[str] = Field(default_factory=lambda: CatalogField[str]())
    long_desc: CatalogField[str] = Field(default_factory=lambda: CatalogField[str]())

    # Overall Evaluation
    overall_trust_status: CatalogTrustStatus = CatalogTrustStatus.UNKNOWN
    overall_confidence: float = 1.0
    has_conflicts: bool = False
    unresolved_conflicts: List[Dict[str, Any]] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "mfg_part_num": self.mfg_part_num,
            "part_desc": self.part_desc,
            "raw_input": self.raw_input.to_dict(),
            "manufacturer_name": self.manufacturer_name.to_dict(),
            "brand_name": self.brand_name.to_dict(),
            "trade_name": self.trade_name.to_dict(),
            "manufacturer_part_number": self.manufacturer_part_number.to_dict(),
            "product_name": self.product_name.to_dict(),
            "series": self.series.to_dict(),
            "classpath": self.classpath.to_dict(),
            "attributes": [a.to_dict() for a in self.attributes],
            "short_desc": self.short_desc.to_dict(),
            "long_desc": self.long_desc.to_dict(),
            "overall_trust_status": self.overall_trust_status.value,
            "overall_confidence": round(self.overall_confidence, 4),
            "has_conflicts": self.has_conflicts,
            "unresolved_conflicts": self.unresolved_conflicts,
        }
