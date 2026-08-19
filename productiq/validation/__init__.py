"""
ProductIQ Validation Package — Phase 3
========================================
Public API for the validation engine.

Phase 3 applies deterministic, explainable rules to NormalizedProduct instances
from Phase 2, producing ValidationFinding instances and ProductValidationReport
objects. No LLM required. Works fully offline.

Usage:
    from productiq.validation import MotorValidator, BatchValidator
    from productiq.validation.models import (
        ProductValidationReport, ValidationFinding,
        ValidationStatus, ValidationSeverity, ValidationCategory,
    )
"""
from productiq.validation.base import BaseValidator
from productiq.validation.models import (
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
    FindingEvidenceRef,
    ValidationFinding,
    ProductValidationReport,
    BatchValidationReport,
)
from productiq.validation.validator import (
    MotorValidator,
    BatchValidator,
)

__all__ = [
    # Base
    "BaseValidator",
    # Models
    "ValidationStatus",
    "ValidationSeverity",
    "ValidationCategory",
    "FindingEvidenceRef",
    "ValidationFinding",
    "ProductValidationReport",
    "BatchValidationReport",
    # Validators
    "MotorValidator",
    "BatchValidator",
]
