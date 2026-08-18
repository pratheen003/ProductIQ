"""
ProductIQ Motor Product Schema
==============================
FROZEN as of Phase 0. All downstream modules MUST import from here.
Never redefine product structure elsewhere.

Status Enum (strict, non-negotiable):
    Verified   — value confirmed from a reliable, cross-checked source
    Inferred   — value derived by calculation or reasonable assumption
    Conflicted — multiple sources disagree; conflict is surfaced, NOT resolved
    Unknown    — no value available; never convert to a guess in Phase 0

Canonical units:
    rated_power        → kW
    rated_voltage      → V
    rated_current      → A
    frequency          → Hz
    rated_speed        → rpm
    poles              → (dimensionless integer)
    efficiency         → % (percentage, 0–100)
    power_factor       → (dimensionless, 0.00–1.00)
    weight             → kg
    ip_rating          → (string, e.g. "IP55")
    frame_size         → (string, e.g. "132M")
"""
from __future__ import annotations

import json
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Status Enum — frozen, strict
# ---------------------------------------------------------------------------

class DataStatus(str, Enum):
    """
    Four-tier data status system for every field value in ProductIQ.
    This enum is the single source of truth — never use raw strings.
    """
    VERIFIED = "Verified"
    INFERRED = "Inferred"
    CONFLICTED = "Conflicted"
    UNKNOWN = "Unknown"


# ---------------------------------------------------------------------------
# Source Type Enum
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    """Enumeration of supported raw source types."""
    PDF = "pdf"
    WEB = "web"
    CSV = "csv"


# ---------------------------------------------------------------------------
# Source Entry — provenance record for a single extracted observation
# ---------------------------------------------------------------------------

class SourceEntry(BaseModel):
    """
    Records exactly where a value came from.
    A field can hold multiple SourceEntry records — required for conflict detection.
    Never discard a SourceEntry once recorded.
    """
    source_id: str = Field(
        ...,
        description="Unique identifier for this source document (e.g. 'WEG_W22SP_brochure_2023')",
    )
    source_type: SourceType = Field(
        ...,
        description="Type of the source: pdf | web | csv",
    )
    location: str = Field(
        ...,
        description="Human-readable location within the source (e.g. 'p.5, Table 1, row 3')",
    )
    reference: str = Field(
        ...,
        description="URL, file path, or other stable reference to the source document",
    )

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Field Value — generic typed container for every technical specification
# ---------------------------------------------------------------------------

V = TypeVar("V")


class FieldValue(BaseModel, Generic[V]):
    """
    Generic container for any technical field value in a motor product record.

    Every technical specification is stored as a FieldValue, never as a bare
    Python primitive. This enables per-field provenance, status tracking, and
    conflict detection throughout the pipeline.

    Rules:
    - `value` may be None only when status is Unknown or Conflicted.
    - `confidence` is a float in [0.0, 1.0] or None when status is Unknown.
    - `sources` must be non-empty for Verified and Inferred status.
    - Multiple sources with differing values → status must be Conflicted.
    """
    value: Optional[V] = Field(
        default=None,
        description="The extracted or computed value. None when status is Unknown.",
    )
    unit: Optional[str] = Field(
        default=None,
        description="Canonical unit string (e.g. 'kW', 'V', 'rpm'). None for dimensionless fields.",
    )
    status: DataStatus = Field(
        default=DataStatus.UNKNOWN,
        description="Data confidence tier: Verified | Inferred | Conflicted | Unknown",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score [0.0, 1.0]. None when status is Unknown.",
    )
    sources: List[SourceEntry] = Field(
        default_factory=list,
        description="All source observations for this field. Preserve every entry — "
                    "never overwrite or discard. Required for conflict detection.",
    )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> DataStatus:
        """Reject any status value not in the canonical four-tier enum."""
        if isinstance(v, DataStatus):
            return v
        try:
            return DataStatus(v)
        except ValueError:
            valid = [s.value for s in DataStatus]
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {valid}. "
                "The four-tier status system is non-negotiable in ProductIQ."
            )

    @model_validator(mode="after")
    def validate_consistency(self) -> "FieldValue[V]":
        """Enforce logical consistency between status, value, confidence, and sources."""
        if self.status == DataStatus.UNKNOWN:
            if self.value is not None:
                raise ValueError(
                    "A field with status=Unknown must have value=None. "
                    "Do not convert Unknown to a guessed value."
                )
        if self.status in (DataStatus.VERIFIED, DataStatus.INFERRED):
            if not self.sources:
                raise ValueError(
                    f"A field with status={self.status.value} must have at least one source entry."
                )
        return self

    model_config = {"frozen": False}


# ---------------------------------------------------------------------------
# Motor Product — the top-level product record
# ---------------------------------------------------------------------------

def _unknown_field(unit: Optional[str] = None) -> FieldValue:
    """Helper: create a default Unknown field with the given canonical unit."""
    return FieldValue(value=None, unit=unit, status=DataStatus.UNKNOWN, confidence=None, sources=[])


class MotorProduct(BaseModel):
    """
    Canonical representation of an industrial electric motor product.

    SCHEMA VERSION: 0.1.0-phase0 (frozen)

    Identity fields are plain strings — they are not wrapped in FieldValue
    because they are stable identifiers, not extracted measurements.

    Every technical specification field is a FieldValue, enabling per-field
    provenance, status tracking, and conflict detection.

    Canonical units (see module docstring for full table):
        rated_power      → kW
        rated_voltage    → V
        rated_current    → A
        frequency        → Hz
        rated_speed      → rpm
        poles            → (dimensionless)
        efficiency       → %
        power_factor     → (dimensionless 0–1)
        weight           → kg
        ip_rating        → (string)
        frame_size       → (string)
    """

    # --- Identity fields ---
    product_id: str = Field(..., description="Unique product identifier (e.g. 'PIQ-W22SP-4P-1.1')")
    manufacturer: str = Field(..., description="Manufacturer name (e.g. 'WEG')")
    model: str = Field(..., description="Model name/series (e.g. 'W22 Severe Process IE3 (4-pole)')")
    product_type: str = Field(default="three_phase_induction_motor", description="Product category")

    # --- Technical specification fields (all FieldValue, all with canonical units) ---
    rated_power: FieldValue = Field(
        default_factory=lambda: _unknown_field("kW"),
        description="Rated shaft output power in kilowatts (kW)",
    )
    rated_voltage: FieldValue = Field(
        default_factory=lambda: _unknown_field("V"),
        description="Rated supply voltage in volts (V)",
    )
    rated_current: FieldValue = Field(
        default_factory=lambda: _unknown_field("A"),
        description="Rated full-load current in amperes (A)",
    )
    frequency: FieldValue = Field(
        default_factory=lambda: _unknown_field("Hz"),
        description="Supply frequency in hertz (Hz)",
    )
    rated_speed: FieldValue = Field(
        default_factory=lambda: _unknown_field("rpm"),
        description="Rated full-load speed in revolutions per minute (rpm)",
    )
    poles: FieldValue = Field(
        default_factory=lambda: _unknown_field(None),
        description="Number of magnetic poles (dimensionless integer, e.g. 4)",
    )
    efficiency: FieldValue = Field(
        default_factory=lambda: _unknown_field("%"),
        description="Full-load efficiency as a percentage (0–100)",
    )
    power_factor: FieldValue = Field(
        default_factory=lambda: _unknown_field(None),
        description="Full-load power factor (dimensionless, 0.00–1.00)",
    )
    weight: FieldValue = Field(
        default_factory=lambda: _unknown_field("kg"),
        description="Motor weight in kilograms (kg)",
    )
    ip_rating: FieldValue = Field(
        default_factory=lambda: _unknown_field(None),
        description="Ingress Protection rating string (e.g. 'IP55', 'IP56')",
    )
    frame_size: FieldValue = Field(
        default_factory=lambda: _unknown_field(None),
        description="IEC frame size designation (e.g. '132M', 'L90S')",
    )

    # Schema version for forward compatibility
    schema_version: str = Field(default="0.1.0-phase0", description="Schema version identifier")

    def to_json(self, indent: int = 2) -> str:
        """Serialize this motor product to a JSON string."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "MotorProduct":
        """Deserialize a motor product from a JSON string."""
        return cls.model_validate(json.loads(json_str))

    @property
    def technical_fields(self) -> dict[str, FieldValue]:
        """Return all technical specification fields as a name→FieldValue mapping."""
        return {
            "rated_power": self.rated_power,
            "rated_voltage": self.rated_voltage,
            "rated_current": self.rated_current,
            "frequency": self.frequency,
            "rated_speed": self.rated_speed,
            "poles": self.poles,
            "efficiency": self.efficiency,
            "power_factor": self.power_factor,
            "weight": self.weight,
            "ip_rating": self.ip_rating,
            "frame_size": self.frame_size,
        }

    @property
    def known_field_count(self) -> int:
        """Count of technical fields that are not Unknown."""
        return sum(
            1 for f in self.technical_fields.values()
            if f.status != DataStatus.UNKNOWN
        )

    model_config = {"frozen": False}


# ---------------------------------------------------------------------------
# Canonical unit registry — single source of truth for unit strings
# ---------------------------------------------------------------------------

CANONICAL_UNITS: dict[str, Optional[str]] = {
    "rated_power":    "kW",
    "rated_voltage":  "V",
    "rated_current":  "A",
    "frequency":      "Hz",
    "rated_speed":    "rpm",
    "poles":          None,       # dimensionless
    "efficiency":     "%",
    "power_factor":   None,       # dimensionless
    "weight":         "kg",
    "ip_rating":      None,       # string descriptor
    "frame_size":     None,       # string descriptor
}
