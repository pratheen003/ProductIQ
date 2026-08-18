"""
ProductIQ Unit Converter — Phase 2
====================================
Deterministic, physics-accurate unit conversion for motor specifications.

Design rules:
- All conversion factors are exact constants — never approximations.
- Every conversion is invertible (for audit purposes).
- Unknown units are NEVER silently converted — they raise UnitConversionError.
- No LLM. No heuristics. Math only.

Supported conversions (Phase 2 scope):
    Power:   W → kW,  HP → kW,  mW → kW
    Mass:    g → kg,  lb → kg,  oz → kg
    Speed:   rpm → rpm (passthrough — already canonical)
    Voltage: V → V (passthrough — already canonical)
    Current: A → A (passthrough — already canonical)
    Freq:    Hz → Hz (passthrough — already canonical)
    Eff:     fraction [0,1] → % (×100), % → % (passthrough)
    PF:      % → fraction (÷100), fraction → fraction (passthrough)
    IP:      string passthrough

CANONICAL_UNITS (from Phase 0 schema):
    rated_power   → kW
    rated_voltage → V
    rated_current → A
    frequency     → Hz
    rated_speed   → rpm
    poles         → None (dimensionless int)
    efficiency    → %
    power_factor  → None (dimensionless 0–1)
    weight        → kg
    ip_rating     → None (string)
    frame_size    → None (string)
"""
from __future__ import annotations

from typing import Optional, Tuple

from productiq.schema import CANONICAL_UNITS


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class UnitConversionError(Exception):
    """Raised when a unit cannot be safely converted to canonical form."""
    pass


# ---------------------------------------------------------------------------
# Unit alias normalization — collapse equivalent spellings to one token
# ---------------------------------------------------------------------------

# Maps raw unit strings (lowercased, stripped) → internal canonical token
_UNIT_ALIASES: dict[str, str] = {
    # Power
    "w":         "W",
    "watt":      "W",
    "watts":     "W",
    "kw":        "kW",
    "kilowatt":  "kW",
    "kilowatts": "kW",
    "mw":        "mW",
    "milliwatt":  "mW",
    "hp":        "HP",
    "horsepower": "HP",
    "cv":        "HP",   # metric HP (1 CV = 0.7457 kW — same as HP for our precision)
    # Mass
    "kg":        "kg",
    "kilogram":  "kg",
    "kilograms": "kg",
    "g":         "g",
    "gram":      "g",
    "grams":     "g",
    "lb":        "lb",
    "lbs":       "lb",
    "pound":     "lb",
    "pounds":    "lb",
    "oz":        "oz",
    "ounce":     "oz",
    "ounces":    "oz",
    # Speed
    "rpm":       "rpm",
    "r/min":     "rpm",
    "rev/min":   "rpm",
    # Voltage
    "v":         "V",
    "volt":      "V",
    "volts":     "V",
    # Current
    "a":         "A",
    "amp":       "A",
    "amps":      "A",
    "ampere":    "A",
    "amperes":   "A",
    # Frequency
    "hz":        "Hz",
    "hertz":     "Hz",
    # Efficiency (percentage)
    "%":         "%",
    "pct":       "%",
    "percent":   "%",
    # Dimensionless (power factor, poles) — treat empty / None as dimensionless
    "":          "dimensionless",
    "pf":        "dimensionless",
    # String fields — normalize to passthrough
    "ip":        "ip_string",
    "frame":     "frame_string",
}

# Exact conversion factors to kW
_TO_KW: dict[str, float] = {
    "W":  1e-3,          # 1 W = 0.001 kW
    "kW": 1.0,
    "mW": 1e-6,          # 1 mW = 0.000001 kW
    "HP": 0.7457,        # 1 HP = 0.7457 kW (IEC standard)
}

# Exact conversion factors to kg
_TO_KG: dict[str, float] = {
    "g":  1e-3,          # 1 g = 0.001 kg
    "kg": 1.0,
    "lb": 0.453592,      # 1 lb = 0.453592 kg (exact NIST value)
    "oz": 0.0283495,     # 1 oz = 0.0283495 kg
}

# Efficiency normalization: fraction [0,1] → percentage [0,100]
_EFF_FRACTION_THRESHOLD = 1.5  # values ≤ 1.5 assumed to be fractions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_unit_string(raw_unit: Optional[str]) -> Optional[str]:
    """
    Normalize a raw unit string to its internal canonical token.

    Args:
        raw_unit: Raw unit string from source (e.g. "KW", "Watt", "lb").

    Returns:
        Normalized token (e.g. "kW", "kg") or None if raw_unit is None/empty.

    Raises:
        UnitConversionError: If the unit string is not empty but is unrecognized.
    """
    if raw_unit is None:
        return None
    normalized = raw_unit.strip().lower()
    if normalized == "":
        return None
    token = _UNIT_ALIASES.get(normalized)
    if token is None:
        # Some multi-part units we want to reject clearly
        raise UnitConversionError(
            f"Unrecognized unit '{raw_unit}'. "
            "Phase 2 cannot safely convert this — preserving as NormalizationIssue."
        )
    return token


def convert_value(
    field_name: str,
    value: float,
    raw_unit: Optional[str],
) -> Tuple[float, str]:
    """
    Convert a numeric value from its raw unit to the canonical unit for
    the given MotorProduct field.

    Args:
        field_name: Canonical MotorProduct field name (e.g. "rated_power").
        value:      Already-parsed numeric value.
        raw_unit:   Unit string from source (normalized internally).

    Returns:
        (canonical_value, canonical_unit) tuple.

    Raises:
        UnitConversionError: If conversion is not supported or unit is unknown.
    """
    canonical_unit = CANONICAL_UNITS.get(field_name)

    # --- Dimensionless fields (poles, power_factor, ip_rating, frame_size) ---
    if canonical_unit is None:
        # Power factor: convert percentage to fraction if needed
        if field_name == "power_factor":
            return _normalize_power_factor(value, raw_unit)
        # poles: must be an integer, no unit needed
        if field_name == "poles":
            return (int(round(value)), None)
        # ip_rating / frame_size: handled separately (string fields)
        return (value, raw_unit)

    # --- Efficiency: % or fraction ---
    if canonical_unit == "%":
        return _normalize_efficiency(value, raw_unit)

    # --- Power: canonical = kW ---
    if canonical_unit == "kW":
        return _convert_power(value, raw_unit)

    # --- Mass: canonical = kg ---
    if canonical_unit == "kg":
        return _convert_mass(value, raw_unit)

    # --- Passthrough units: V, A, Hz, rpm ---
    if canonical_unit in ("V", "A", "Hz", "rpm"):
        return _passthrough(field_name, value, raw_unit, canonical_unit)

    raise UnitConversionError(
        f"No conversion rule for field '{field_name}' with canonical unit '{canonical_unit}'."
    )


def is_equivalent(
    field_name: str,
    value_a: Optional[float],
    unit_a: Optional[str],
    value_b: Optional[float],
    unit_b: Optional[str],
    tolerance: float = 1e-6,
) -> bool:
    """
    Return True if two normalized values for the same field are equivalent
    within floating-point tolerance.

    Both values must already be in canonical units.
    """
    if value_a is None or value_b is None:
        return value_a is value_b  # None == None only
    if unit_a != unit_b:
        return False
    return abs(value_a - value_b) <= tolerance


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _convert_power(value: float, raw_unit: Optional[str]) -> Tuple[float, str]:
    """Convert any power unit to kW."""
    token = normalize_unit_string(raw_unit) if raw_unit else "kW"
    factor = _TO_KW.get(token)
    if factor is None:
        raise UnitConversionError(
            f"Cannot convert power unit '{raw_unit}' to kW. "
            f"Supported: {list(_TO_KW.keys())}"
        )
    result = round(value * factor, 6)
    return (result, "kW")


def _convert_mass(value: float, raw_unit: Optional[str]) -> Tuple[float, str]:
    """Convert any mass unit to kg."""
    token = normalize_unit_string(raw_unit) if raw_unit else "kg"
    factor = _TO_KG.get(token)
    if factor is None:
        raise UnitConversionError(
            f"Cannot convert mass unit '{raw_unit}' to kg. "
            f"Supported: {list(_TO_KG.keys())}"
        )
    result = round(value * factor, 6)
    return (result, "kg")


def _normalize_efficiency(value: float, raw_unit: Optional[str]) -> Tuple[float, str]:
    """
    Normalize efficiency to percentage [0, 100].
    - If value ≤ 1.5 and unit is dimensionless → treat as fraction, multiply by 100.
    - If value > 1.5 or unit is '%' → already percentage.
    """
    token = normalize_unit_string(raw_unit) if raw_unit else None
    if token == "%" or value > _EFF_FRACTION_THRESHOLD:
        # Already a percentage
        result = round(value, 6)
    else:
        # Fraction → convert to percentage
        result = round(value * 100.0, 6)
    return (result, "%")


def _normalize_power_factor(value: float, raw_unit: Optional[str]) -> Tuple[float, None]:
    """
    Normalize power factor to dimensionless fraction [0.0, 1.0].
    - If value > 1.5 and unit is '%' → treat as percentage, divide by 100.
    - Otherwise → already fraction.
    """
    token = normalize_unit_string(raw_unit) if raw_unit else None
    if token == "%" and value > 1.5:
        result = round(value / 100.0, 6)
    else:
        result = round(value, 6)
    return (result, None)


def _passthrough(
    field_name: str,
    value: float,
    raw_unit: Optional[str],
    canonical_unit: str,
) -> Tuple[float, str]:
    """
    For units that are already canonical (V, A, Hz, rpm): verify and pass through.
    Raises UnitConversionError only if a conflicting unit is detected.
    """
    if raw_unit is None:
        # Accept None unit for these fields — unit may be implied
        return (value, canonical_unit)
    try:
        token = normalize_unit_string(raw_unit)
    except UnitConversionError:
        raise UnitConversionError(
            f"Field '{field_name}': unrecognized unit '{raw_unit}'. "
            f"Expected canonical unit '{canonical_unit}'."
        )
    if token != canonical_unit:
        raise UnitConversionError(
            f"Field '{field_name}': cannot convert unit '{raw_unit}' (→ '{token}') "
            f"to canonical '{canonical_unit}' without a defined conversion factor."
        )
    return (value, canonical_unit)
