"""
ProductIQ Normalization Package — Phase 2
==========================================
Public API for the normalization layer.

Phase 2 transforms raw EvidenceRecord observations (from Phase 1 extraction)
into normalized, canonical NormalizedProduct instances with full provenance
preservation, deterministic unit conversion, and conflict surfacing.

Usage:
    from productiq.normalization import MotorNormalizer, BatchNormalizer
    from productiq.normalization.models import NormalizedProduct, NormalizedField
    from productiq.normalization.unit_converter import convert_value
    from productiq.normalization.attribute_mapper import get_mapping
"""
from productiq.normalization.base import BaseNormalizer
from productiq.normalization.models import (
    ConflictRecord,
    EvidenceRef,
    NormalizationIssue,
    NormalizationOutcome,
    NormalizationReport,
    NormalizedField,
    NormalizedProduct,
)
from productiq.normalization.unit_converter import (
    UnitConversionError,
    convert_value,
    normalize_unit_string,
    is_equivalent,
)
from productiq.normalization.value_parser import (
    ValueParseError,
    parse_numeric,
    parse_ip_rating,
    parse_frame_size,
    parse_poles,
    safe_parse_float,
)
from productiq.normalization.attribute_mapper import (
    MappingKind,
    get_mapping,
    get_canonical_field,
    is_canonical,
    all_canonical_fields,
)
from productiq.normalization.normalizer import (
    MotorNormalizer,
    BatchNormalizer,
)

__all__ = [
    # Base
    "BaseNormalizer",
    # Models
    "NormalizedProduct",
    "NormalizedField",
    "EvidenceRef",
    "ConflictRecord",
    "NormalizationIssue",
    "NormalizationOutcome",
    "NormalizationReport",
    # Unit conversion
    "convert_value",
    "normalize_unit_string",
    "is_equivalent",
    "UnitConversionError",
    # Value parsing
    "parse_numeric",
    "parse_ip_rating",
    "parse_frame_size",
    "parse_poles",
    "safe_parse_float",
    "ValueParseError",
    # Attribute mapping
    "MappingKind",
    "get_mapping",
    "get_canonical_field",
    "is_canonical",
    "all_canonical_fields",
    # Normalizers
    "MotorNormalizer",
    "BatchNormalizer",
]
