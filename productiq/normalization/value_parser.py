"""
ProductIQ Value Parser — Phase 2
==================================
Safe, deterministic parsing of raw value strings from evidence records.

Design rules:
- Never fabricate a value on parse failure — raise ValueParseError instead.
- Never modify values semantically — parse only.
- Handle realistic manufacturer formatting quirks without being dangerously broad.
- String fields (ip_rating, frame_size) are returned as-is after stripping.

Parsing handles:
  - Plain numerics: "1.1", "1455", "0.80", "84.8"
  - Numeric with unit suffix: "1.1 kW", "19.5 kg", "1455 rpm", "400 V"
  - Percentage: "84.8 %", "84.8%"
  - Fraction strings: "0.80" (power_factor)
  - Phase strings: "3", "3 phase", "three phase" → 3
  - Pole count: "4", "6", "4 poles" → 4
  - Frame size strings: "90S", "L90S", "132M" (returned as str)
  - IP rating strings: "IP55", "IP56", "56" (returned as-is with normalization)
  - Ratio values: "7.6" (dimensionless, returned as float)
"""
from __future__ import annotations

import re
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class ValueParseError(Exception):
    """Raised when a raw value string cannot be safely parsed."""
    pass


# ---------------------------------------------------------------------------
# Compiled patterns (compiled once at module load for performance)
# ---------------------------------------------------------------------------

# Matches: optional sign, integer or decimal, optional unit suffix
# Examples: "1.1 kW", "1455", "84.8 %", "19.5 kg", "-0.5"
_NUMERIC_WITH_UNIT = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z%°()./\-]*)\s*$"
)

# Phase / pole string matchers
_THREE_PHASE = re.compile(r"(?:3|three|3[\s-]*phase)", re.IGNORECASE)
_POLE_COUNT  = re.compile(r"(\d+)\s*(?:poles?|pole)?", re.IGNORECASE)

# IP rating: "IP55", "IP56", "55", "56"
_IP_PATTERN = re.compile(r"(?:IP\s*)?(\d{2,3})", re.IGNORECASE)

# Frame size: alphanumeric strings like "90S", "L90S", "132M"
_FRAME_PATTERN = re.compile(r"^[A-Za-z0-9]+$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_numeric(raw_value: str, field_name: str = "") -> Tuple[float, Optional[str]]:
    """
    Parse a raw string value into (float, unit_string).

    Args:
        raw_value:  Raw string from EvidenceRecord (e.g. "1.1 kW", "84.8 %").
        field_name: Used only in error messages for context.

    Returns:
        (numeric_value, unit_string_or_None)

    Raises:
        ValueParseError: If the string cannot be safely parsed as a number.
    """
    if not isinstance(raw_value, str):
        raise ValueParseError(
            f"Field '{field_name}': expected a string raw_value, "
            f"got {type(raw_value).__name__}: {raw_value!r}"
        )

    stripped = raw_value.strip()
    if not stripped:
        raise ValueParseError(
            f"Field '{field_name}': raw_value is empty or whitespace-only."
        )

    m = _NUMERIC_WITH_UNIT.match(stripped)
    if not m:
        raise ValueParseError(
            f"Field '{field_name}': cannot parse '{raw_value}' as a numeric value. "
            "Expected format: number optionally followed by a unit string."
        )

    numeric_str = m.group(1)
    unit_str    = m.group(2).strip() or None

    try:
        numeric_value = float(numeric_str)
    except ValueError:
        raise ValueParseError(
            f"Field '{field_name}': numeric conversion failed for '{numeric_str}' "
            f"(from raw_value '{raw_value}')."
        )

    return (numeric_value, unit_str)


def parse_string_field(raw_value: str, field_name: str = "") -> str:
    """
    Parse a string-typed canonical field (ip_rating, frame_size).
    Returns the stripped value. Raises ValueParseError if empty.
    """
    if not isinstance(raw_value, str):
        raise ValueParseError(
            f"Field '{field_name}': expected string, got {type(raw_value).__name__}"
        )
    stripped = raw_value.strip()
    if not stripped:
        raise ValueParseError(
            f"Field '{field_name}': raw_value is empty — no string value to preserve."
        )
    return stripped


def parse_ip_rating(raw_value: str) -> str:
    """
    Parse an IP rating from a raw string.
    Handles: "IP55", "IP56", "55", "56", "IP56+ sealing described...".

    Returns normalized string like "IP56" or the stripped input if no match.
    """
    stripped = raw_value.strip()
    # Full match "IP\d+" anywhere in the string
    m = re.search(r"IP\s*(\d{2,3})", stripped, re.IGNORECASE)
    if m:
        return f"IP{m.group(1)}"
    # Bare number like "56" or "55"
    m2 = re.match(r"^\s*(\d{2,3})\s*$", stripped)
    if m2:
        return f"IP{m2.group(1)}"
    # Return stripped as-is (e.g. "IP56+ sealing described" — preserve verbatim)
    return stripped


def parse_frame_size(raw_value: str) -> str:
    """
    Parse a frame size designation.
    Handles: "90S", "L90S", "132M", "160L".

    Returns the raw_value stripped. Frame size strings are opaque
    designations — we preserve them as-is without interpretation.
    """
    return raw_value.strip()


def parse_poles(raw_value: str) -> int:
    """
    Parse pole count from various formats:
    "4", "6", "4 poles", "4-pole".

    Returns int.
    Raises ValueParseError if cannot parse.
    """
    stripped = raw_value.strip()
    m = _POLE_COUNT.match(stripped)
    if m:
        return int(m.group(1))
    raise ValueParseError(
        f"Cannot parse poles from '{raw_value}'. Expected integer or 'N poles'."
    )


def parse_phase(raw_value: str) -> int:
    """
    Parse phase count. "3", "3 phase", "three phase" → 3.
    Returns int.
    Raises ValueParseError if not recognizable.
    """
    stripped = raw_value.strip()
    # Direct integer
    try:
        return int(stripped)
    except ValueError:
        pass
    if _THREE_PHASE.search(stripped):
        return 3
    raise ValueParseError(
        f"Cannot parse phase from '{raw_value}'."
    )


def safe_parse_float(raw_value: str, field_name: str = "") -> float:
    """
    Parse a raw string that is expected to be a plain numeric (already parsed
    by the extractor, stored as string in raw_value).

    Uses parse_numeric and discards the unit (which must already be stored
    separately in the EvidenceRecord.unit field).
    """
    value, _ = parse_numeric(raw_value, field_name=field_name)
    return value
