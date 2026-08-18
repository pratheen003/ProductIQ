"""
ProductIQ Attribute Mapper — Phase 2
======================================
Deterministic mapping from Phase 1 EvidenceRecord attribute names to
Phase 0 canonical MotorProduct field names.

Design rules:
- Mapping is explicit and documented — no guessing via string similarity.
- Unmapped attributes are flagged as UNMAPPED, never silently dropped.
- Multiple evidence attributes can map to the same canonical field.
- Metadata / unit columns (e.g. "rated_power_unit") are recognized as
  METADATA and excluded from canonical field building.
- Phase 2 does NOT decide which of multiple conflicting mappings is
  "correct" — that is Phase 3's job.

Canonical fields (from Phase 0 CANONICAL_UNITS):
    rated_power      kW
    rated_voltage    V
    rated_current    A
    frequency        Hz
    rated_speed      rpm
    poles            (dimensionless int)
    efficiency       %
    power_factor     (dimensionless 0–1)
    weight           kg
    ip_rating        (string)
    frame_size       (string)
"""
from __future__ import annotations

from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Mapping intent — what we should do with this attribute
# ---------------------------------------------------------------------------

class MappingKind(str, Enum):
    CANONICAL  = "canonical"   # Maps to a MotorProduct canonical field
    METADATA   = "metadata"    # Auxiliary / unit column — informational only
    UNMAPPED   = "unmapped"    # No known mapping — preserve as unmapped evidence
    SKIP       = "skip"        # Intentionally ignored (e.g. full-text source_ref rows)


# ---------------------------------------------------------------------------
# Attribute mapping table
# ---------------------------------------------------------------------------
# Format: evidence_attribute_name -> (canonical_field_or_None, MappingKind, note)
#
# EVIDENCE ATTRIBUTE         CANONICAL FIELD     KIND        NOTE
_ATTRIBUTE_MAP: dict[str, tuple[Optional[str], MappingKind, str]] = {

    # ---- Power ----------------------------------------------------------------
    "rated_power":              ("rated_power",     MappingKind.CANONICAL,  "Power in kW (already canonical)"),
    "rated_power_kw":           ("rated_power",     MappingKind.CANONICAL,  "Power in kW — explicit kW column"),
    "rated_power_hp":           ("rated_power",     MappingKind.CANONICAL,  "Power in HP → convert to kW"),
    "rated_power_raw":          ("rated_power",     MappingKind.CANONICAL,  "Power with embedded unit string"),
    "rated_power_unit":         (None,              MappingKind.METADATA,   "Unit column for rated_power — skip"),
    "rated_power_w":            ("rated_power",     MappingKind.CANONICAL,  "Power in W → convert to kW"),

    # ---- Voltage --------------------------------------------------------------
    "rated_voltage":            ("rated_voltage",   MappingKind.CANONICAL,  "Voltage in V (already canonical)"),
    "rated_voltage_v":          ("rated_voltage",   MappingKind.CANONICAL,  "Voltage in V — explicit V column"),

    # ---- Current --------------------------------------------------------------
    "rated_current":            ("rated_current",   MappingKind.CANONICAL,  "Current in A (already canonical)"),
    "full_load_current":        ("rated_current",   MappingKind.CANONICAL,  "Full load current → rated_current"),
    "full_load_current_a":      ("rated_current",   MappingKind.CANONICAL,  "Full load current in A"),
    "rated_current_unit":       (None,              MappingKind.METADATA,   "Unit column for rated_current — skip"),

    # ---- Frequency ------------------------------------------------------------
    "frequency":                ("frequency",       MappingKind.CANONICAL,  "Frequency in Hz (already canonical)"),
    "frequency_hz":             ("frequency",       MappingKind.CANONICAL,  "Frequency in Hz — explicit Hz column"),

    # ---- Speed ----------------------------------------------------------------
    "rated_speed":              ("rated_speed",     MappingKind.CANONICAL,  "Speed in rpm (already canonical)"),
    "rated_speed_rpm":          ("rated_speed",     MappingKind.CANONICAL,  "Speed in rpm — explicit rpm column"),

    # ---- Poles ----------------------------------------------------------------
    "poles":                    ("poles",           MappingKind.CANONICAL,  "Pole count (dimensionless int)"),
    "num_poles":                ("poles",           MappingKind.CANONICAL,  "Number of poles"),
    "pole_count":               ("poles",           MappingKind.CANONICAL,  "Number of poles"),

    # ---- Efficiency -----------------------------------------------------------
    "efficiency":               ("efficiency",      MappingKind.CANONICAL,  "Full-load efficiency %"),
    "efficiency_percent":       ("efficiency",      MappingKind.CANONICAL,  "Efficiency in %"),
    "efficiency_pct":           ("efficiency",      MappingKind.CANONICAL,  "Efficiency in %"),
    "efficiency_at_100pct_load": ("efficiency",     MappingKind.CANONICAL,  "100% load efficiency"),
    # Partial-load efficiency — not a canonical field, preserve as unmapped
    "efficiency_at_50pct_load": (None,              MappingKind.UNMAPPED,   "50% load efficiency — no canonical field"),
    "efficiency_at_75pct_load": (None,              MappingKind.UNMAPPED,   "75% load efficiency — no canonical field"),

    # ---- Power Factor ---------------------------------------------------------
    "power_factor":             ("power_factor",    MappingKind.CANONICAL,  "Full-load power factor (dimensionless)"),
    "power_factor_pct":         ("power_factor",    MappingKind.CANONICAL,  "Power factor in % → convert to fraction"),
    # Partial-load power factor — no canonical field
    "power_factor_at_50pct_load": (None,            MappingKind.UNMAPPED,   "50% load PF — no canonical field"),
    "power_factor_at_75pct_load": (None,            MappingKind.UNMAPPED,   "75% load PF — no canonical field"),

    # ---- Weight ---------------------------------------------------------------
    "weight":                   ("weight",          MappingKind.CANONICAL,  "Weight in kg (already canonical)"),
    "weight_kg":                ("weight",          MappingKind.CANONICAL,  "Weight in kg — explicit kg column"),
    "weight_g":                 ("weight",          MappingKind.CANONICAL,  "Weight in g → convert to kg"),
    "weight_lb":                ("weight",          MappingKind.CANONICAL,  "Weight in lb → convert to kg"),

    # ---- IP Rating ------------------------------------------------------------
    "ip_rating":                ("ip_rating",       MappingKind.CANONICAL,  "IP rating string"),
    "ip_rating_note":           ("ip_rating",       MappingKind.CANONICAL,  "IP rating note — extract IP code"),
    "ingress_protection":       ("ip_rating",       MappingKind.CANONICAL,  "Ingress protection rating"),

    # ---- Frame Size -----------------------------------------------------------
    "frame_size":               ("frame_size",      MappingKind.CANONICAL,  "IEC frame size designation"),
    "frame":                    ("frame_size",      MappingKind.CANONICAL,  "IEC frame designation (short column)"),
    "frame_designation":        ("frame_size",      MappingKind.CANONICAL,  "IEC frame designation"),

    # ---- Non-canonical technical fields (preserve as unmapped) ---------------
    "full_load_torque_nm":      (None,              MappingKind.UNMAPPED,   "Torque in Nm — no MotorProduct field"),
    "full_load_torque":         (None,              MappingKind.UNMAPPED,   "Full load torque — no canonical field"),
    "locked_rotor_current_ratio":(None,             MappingKind.UNMAPPED,   "LRC ratio — no canonical field"),
    "locked_rotor_torque_ratio":(None,              MappingKind.UNMAPPED,   "LRT ratio — no canonical field"),
    "breakdown_torque_ratio":   (None,              MappingKind.UNMAPPED,   "BDT ratio — no canonical field"),
    "inertia_kgm2":             (None,              MappingKind.UNMAPPED,   "Moment of inertia — no canonical field"),
    "locked_rotor_time_hot_s":  (None,              MappingKind.UNMAPPED,   "LR time hot — no canonical field"),
    "locked_rotor_time_cold_s": (None,              MappingKind.UNMAPPED,   "LR time cold — no canonical field"),
    "sound_dba":                (None,              MappingKind.UNMAPPED,   "Sound level dB(A) — no canonical field"),

    # ---- Pure metadata / skip columns ----------------------------------------
    "source_location":          (None,              MappingKind.SKIP,       "Source reference text — skip"),
    "current_unit":             (None,              MappingKind.METADATA,   "Unit column — skip"),
    "manufacturer":             (None,              MappingKind.SKIP,       "Identity field — skip (from manifest)"),
    "model":                    (None,              MappingKind.SKIP,       "Identity field — skip (from manifest)"),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_mapping(attribute: str) -> tuple[Optional[str], MappingKind, str]:
    """
    Look up the canonical mapping for an evidence attribute.

    Args:
        attribute: Evidence attribute name (e.g. "rated_power_hp").

    Returns:
        (canonical_field_or_None, MappingKind, note)
        - canonical_field is None for METADATA, UNMAPPED, SKIP kinds.
    """
    # Exact match first
    result = _ATTRIBUTE_MAP.get(attribute)
    if result is not None:
        return result

    # Case-insensitive fallback
    lower = attribute.lower()
    for key, val in _ATTRIBUTE_MAP.items():
        if key.lower() == lower:
            return val

    # Not in the map — treat as unmapped
    return (None, MappingKind.UNMAPPED, f"Unknown attribute '{attribute}' — no mapping defined")


def is_canonical(attribute: str) -> bool:
    """Return True if this attribute maps to a canonical MotorProduct field."""
    _, kind, _ = get_mapping(attribute)
    return kind == MappingKind.CANONICAL


def get_canonical_field(attribute: str) -> Optional[str]:
    """
    Return the canonical MotorProduct field name for an evidence attribute,
    or None if it does not map to a canonical field.
    """
    canonical, kind, _ = get_mapping(attribute)
    if kind == MappingKind.CANONICAL:
        return canonical
    return None


def all_canonical_fields() -> list[str]:
    """Return all MotorProduct canonical field names (from Phase 0)."""
    from productiq.schema import CANONICAL_UNITS
    return list(CANONICAL_UNITS.keys())
