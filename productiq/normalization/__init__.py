"""
ProductIQ Normalization Module
------------------------------
Phase 2 target: Convert extracted raw values into canonical units.

Responsibilities:
- Convert HP → kW, V (various configs) → V, rpm variants, etc.
- Standardize field names from legacy naming conventions
- Preserve original raw value and unit in SourceEntry before conversion

PHASE 0 STATUS: Stub only.

Non-negotiable rule: normalization must NEVER silently discard the original
value. The SourceEntry must record both the raw extracted value and the
canonical converted value, so auditors can trace every transformation.
"""
