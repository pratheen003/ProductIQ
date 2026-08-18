"""
ProductIQ Schema Package
------------------------
Exports the canonical motor schema types.
All pipeline modules must import from here — never redefine product structure.
"""
from .motor import (
    CANONICAL_UNITS,
    DataStatus,
    FieldValue,
    MotorProduct,
    SourceEntry,
    SourceType,
)

__all__ = [
    "DataStatus",
    "SourceType",
    "SourceEntry",
    "FieldValue",
    "MotorProduct",
    "CANONICAL_UNITS",
]
