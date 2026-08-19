"""
ProductIQ Validation Rules — Phase 3
======================================
All validation rules organized by category.

Rule ID naming convention:
  <CATEGORY>_<FIELD>_<CHECK>
  e.g. RANGE_RATED_POWER_POSITIVE
       CONSISTENCY_RATED_CURRENT_CROSS_SOURCE
       ENGINEERING_TORQUE_POWER_RPM

Every rule is:
  1. Deterministic — same input always produces same output
  2. Explainable — every result includes a human-readable reason
  3. Defensible — every threshold is documented and justified
  4. Independent — rules don't call other rules
  5. Offline-capable — no LLM, no network required

Tolerance documentation:
  - Numeric equivalence tolerance: 1e-4 (covers unit conversion rounding)
  - Torque-power-rpm tolerance: 15% (covers measurement conditions, rounding,
    and the fact that shaft power vs electrical power can differ)
  - Power factor tolerance: 0.005 (covers rounding in spec sheets)
"""
from __future__ import annotations

import math
from typing import List, Optional, Any

from productiq.validation.models import (
    ValidationCategory,
    ValidationFinding,
    ValidationSeverity,
    ValidationStatus,
    FindingEvidenceRef,
)
from productiq.normalization.models import (
    NormalizedField,
    NormalizedProduct,
    NormalizationOutcome,
    EvidenceRef,
    ConflictRecord,
)


# ---------------------------------------------------------------------------
# Tolerance constants — documented and justified
# ---------------------------------------------------------------------------

# Numeric value equivalence: covers single-precision rounding and unit conversion
_NUMERIC_TOL = 1e-4

# Torque/power/RPM: 15% tolerance
#   Justification: manufacturer tables round values, efficiency is temperature-
#   dependent, and slip varies with load conditions. 15% is conservative enough
#   to catch real data errors while not rejecting valid spec-sheet values.
_TORQUE_TOL_FRACTION = 0.15

# Efficiency bounds for IE3 class motors (IEC 60034-30-1):
#   IE3 efficiency class requires η ≥ ~85% at rated load for small motors.
#   We use a relaxed lower bound of 0% to allow for edge cases.
#   Upper bound is 100% (physical maximum).
_EFFICIENCY_MIN_PCT = 0.0   # inclusive lower bound
_EFFICIENCY_MAX_PCT = 100.0  # inclusive upper bound

# Power factor physical bounds: 0 ≤ PF ≤ 1 (0.0 inclusive is valid for no-load)
_PF_MIN = 0.0
_PF_MAX = 1.0

# Current: must be strictly positive (> 0) if present
_CURRENT_STRICT_MIN = 0.0   # value must be > this

# Speed: must be strictly positive (> 0) if present
_SPEED_STRICT_MIN = 0.0     # value must be > this

# Weight: must be strictly positive (> 0) if present
_WEIGHT_STRICT_MIN = 0.0    # value must be > this

# Power: must be strictly positive (> 0) if present
_POWER_STRICT_MIN = 0.0     # value must be > this

# Voltage: must be strictly positive (> 0) if present
_VOLTAGE_STRICT_MIN = 0.0   # value must be > this


# ---------------------------------------------------------------------------
# Helper to build a FindingEvidenceRef from an EvidenceRef
# ---------------------------------------------------------------------------

def _ref(ev: Optional[EvidenceRef]) -> Optional[FindingEvidenceRef]:
    if ev is None:
        return None
    return FindingEvidenceRef(
        source_id=ev.source_id,
        source_type=ev.source_type,
        attribute=ev.attribute,
        raw_value=ev.raw_value,
        raw_unit=ev.raw_unit,
        page=ev.page,
        row=ev.row,
        column=ev.column,
        section=ev.section,
    )


def _refs_from_field(nf: NormalizedField) -> List[FindingEvidenceRef]:
    return [r for ev in nf.evidence_refs for r in [_ref(ev)] if r is not None]


# ---------------------------------------------------------------------------
# A. Schema validation rules
# ---------------------------------------------------------------------------

def check_schema_canonical_units(product: NormalizedProduct) -> List[ValidationFinding]:
    """
    A.1 SCHEMA_CANONICAL_UNITS
    Verify that each field's canonical_unit matches the Phase 0 CANONICAL_UNITS registry.
    """
    from productiq.schema import CANONICAL_UNITS

    findings = []
    for field_name, nf in product.fields.items():
        if nf.outcome == NormalizationOutcome.MISSING:
            continue

        expected_unit = CANONICAL_UNITS.get(field_name)
        actual_unit = nf.canonical_unit

        # Dimensionless fields: both should be None
        if expected_unit is None and actual_unit is not None:
            findings.append(ValidationFinding(
                rule_id="SCHEMA_CANONICAL_UNITS",
                category=ValidationCategory.SCHEMA,
                status=ValidationStatus.FAIL,
                severity=ValidationSeverity.HIGH,
                field=field_name,
                description="Field should be dimensionless (unit=None)",
                actual_value=actual_unit,
                expected_condition="canonical_unit = None",
                explanation=(
                    f"Field '{field_name}' is dimensionless per CANONICAL_UNITS "
                    f"but has unit='{actual_unit}'. "
                    "Check Phase 2 normalization configuration."
                ),
                evidence_refs=_refs_from_field(nf),
            ))
        elif expected_unit is not None and actual_unit != expected_unit:
            findings.append(ValidationFinding(
                rule_id="SCHEMA_CANONICAL_UNITS",
                category=ValidationCategory.SCHEMA,
                status=ValidationStatus.FAIL,
                severity=ValidationSeverity.HIGH,
                field=field_name,
                description=f"Field unit must be '{expected_unit}'",
                actual_value=actual_unit,
                expected_condition=f"canonical_unit = '{expected_unit}'",
                explanation=(
                    f"Field '{field_name}' has canonical_unit='{actual_unit}' "
                    f"but Phase 0 CANONICAL_UNITS requires '{expected_unit}'. "
                    "This is a normalization error."
                ),
                evidence_refs=_refs_from_field(nf),
            ))
        else:
            findings.append(ValidationFinding(
                rule_id="SCHEMA_CANONICAL_UNITS",
                category=ValidationCategory.SCHEMA,
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                field=field_name,
                description=f"Canonical unit check",
                actual_value=actual_unit,
                expected_condition=f"canonical_unit = '{expected_unit}'",
                explanation=(
                    f"Field '{field_name}' has correct canonical unit: "
                    f"'{actual_unit}' (expected '{expected_unit}')."
                ),
                evidence_refs=_refs_from_field(nf),
            ))
    return findings


def check_schema_normalization_version(product: NormalizedProduct) -> List[ValidationFinding]:
    """
    A.2 SCHEMA_NORMALIZATION_VERSION
    Verify the normalized product carries a recognized normalization version.
    """
    expected = "2.0.0"
    actual = product.normalization_version
    if actual == expected:
        return [ValidationFinding(
            rule_id="SCHEMA_NORMALIZATION_VERSION",
            category=ValidationCategory.SCHEMA,
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            field="(product)",
            description="Normalization version check",
            actual_value=actual,
            expected_condition=f"normalization_version = '{expected}'",
            explanation=f"Normalized product uses recognized version '{actual}'.",
        )]
    return [ValidationFinding(
        rule_id="SCHEMA_NORMALIZATION_VERSION",
        category=ValidationCategory.SCHEMA,
        status=ValidationStatus.WARNING,
        severity=ValidationSeverity.LOW,
        field="(product)",
        description="Normalization version check",
        actual_value=actual,
        expected_condition=f"normalization_version = '{expected}'",
        explanation=(
            f"Normalized product version is '{actual}', expected '{expected}'. "
            "This may indicate a schema evolution that needs review."
        ),
    )]


# ---------------------------------------------------------------------------
# B. Required-field validation
# ---------------------------------------------------------------------------

# Fields that must have evidence for a product to be minimally usable
_REQUIRED_FIELDS = {"rated_power", "rated_voltage", "rated_speed"}

# Fields that are important but not strictly required
_IMPORTANT_FIELDS = {"rated_current", "efficiency", "weight"}


def check_required_fields(product: NormalizedProduct) -> List[ValidationFinding]:
    """
    B.1 REQUIRED_FIELD_PRESENCE
    Verify that required technical fields have at least some evidence.
    A field is 'present' if it has evidence (even if conflicted).
    Missing means no evidence at all.
    """
    findings = []
    for field_name in _REQUIRED_FIELDS:
        nf = product.fields.get(field_name)
        if nf is None or nf.outcome == NormalizationOutcome.MISSING:
            findings.append(ValidationFinding(
                rule_id="REQUIRED_FIELD_PRESENCE",
                category=ValidationCategory.REQUIRED_FIELD,
                status=ValidationStatus.FAIL,
                severity=ValidationSeverity.HIGH,
                field=field_name,
                description=f"Required field '{field_name}' must have evidence",
                actual_value=None,
                expected_condition="field must have at least one evidence record",
                explanation=(
                    f"Required field '{field_name}' has no evidence from any source. "
                    "This field is necessary for basic product characterization."
                ),
            ))
        else:
            findings.append(ValidationFinding(
                rule_id="REQUIRED_FIELD_PRESENCE",
                category=ValidationCategory.REQUIRED_FIELD,
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                field=field_name,
                description=f"Required field '{field_name}' presence check",
                actual_value=nf.canonical_value,
                expected_condition="field must have at least one evidence record",
                explanation=(
                    f"Required field '{field_name}' has {len(nf.evidence_refs)} "
                    f"evidence reference(s), outcome='{nf.outcome.value}'."
                ),
                evidence_refs=_refs_from_field(nf),
            ))
    return findings


def check_important_fields(product: NormalizedProduct) -> List[ValidationFinding]:
    """
    B.2 IMPORTANT_FIELD_PRESENCE
    Warn about missing important (but not strictly required) fields.
    """
    findings = []
    for field_name in _IMPORTANT_FIELDS:
        nf = product.fields.get(field_name)
        if nf is None or nf.outcome == NormalizationOutcome.MISSING:
            findings.append(ValidationFinding(
                rule_id="IMPORTANT_FIELD_PRESENCE",
                category=ValidationCategory.MISSING_DATA,
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.MEDIUM,
                field=field_name,
                description=f"Important field '{field_name}' is missing",
                actual_value=None,
                expected_condition="field should have evidence",
                explanation=(
                    f"Field '{field_name}' has no evidence from any source. "
                    "This field is important for full product characterization "
                    "but is not strictly required."
                ),
            ))
        else:
            findings.append(ValidationFinding(
                rule_id="IMPORTANT_FIELD_PRESENCE",
                category=ValidationCategory.MISSING_DATA,
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                field=field_name,
                description=f"Important field '{field_name}' presence check",
                actual_value=nf.canonical_value,
                expected_condition="field should have evidence",
                explanation=(
                    f"Field '{field_name}' has evidence, outcome='{nf.outcome.value}'."
                ),
                evidence_refs=_refs_from_field(nf),
            ))
    return findings


def check_missing_data_inventory(product: NormalizedProduct) -> List[ValidationFinding]:
    """
    H.1 MISSING_DATA_INVENTORY
    Record all fields with no evidence — honest reporting, not errors.
    """
    findings = []
    for field_name, nf in product.fields.items():
        if nf.outcome == NormalizationOutcome.MISSING:
            # Only report if not already covered by required/important checks
            if field_name not in _REQUIRED_FIELDS and field_name not in _IMPORTANT_FIELDS:
                findings.append(ValidationFinding(
                    rule_id="MISSING_DATA_INVENTORY",
                    category=ValidationCategory.MISSING_DATA,
                    status=ValidationStatus.NOT_CHECKED,
                    severity=ValidationSeverity.LOW,
                    field=field_name,
                    description=f"Field '{field_name}' has no evidence",
                    actual_value=None,
                    expected_condition="N/A — optional field",
                    explanation=(
                        f"Optional field '{field_name}' has no evidence from any source. "
                        "This is recorded for completeness; it is not an error for optional fields."
                    ),
                ))
    return findings


# ---------------------------------------------------------------------------
# D. Range / plausibility validation
# ---------------------------------------------------------------------------

def _numeric_field_range_check(
    product: NormalizedProduct,
    field_name: str,
    min_val: Optional[float],
    max_val: Optional[float],
    rule_id: str,
    description: str,
    severity: ValidationSeverity = ValidationSeverity.HIGH,
    strict_min: bool = False,  # If True, val must be strictly > min_val (not >=)
) -> List[ValidationFinding]:
    """Generic numeric range check helper."""
    nf = product.fields.get(field_name)
    if nf is None or nf.outcome == NormalizationOutcome.MISSING:
        return [ValidationFinding(
            rule_id=rule_id,
            category=ValidationCategory.RANGE,
            status=ValidationStatus.NOT_CHECKED,
            severity=ValidationSeverity.LOW,
            field=field_name,
            description=description,
            actual_value=None,
            expected_condition=_range_condition_str(min_val, max_val),
            explanation=f"Field '{field_name}' has no value — range check skipped.",
        )]

    # Conflict: check the conflict values individually
    if nf.outcome == NormalizationOutcome.CONFLICT:
        # Check each conflict pair's values against the range
        all_values = []
        for c in nf.conflicts:
            if c.value_a is not None:
                all_values.append((c.value_a, c.unit_a, c.source_a))
            if c.value_b is not None:
                all_values.append((c.value_b, c.unit_b, c.source_b))
        # Also check raw evidence refs
        for ev in nf.evidence_refs:
            if ev.parsed_value is not None:
                all_values.append((ev.parsed_value, ev.raw_unit, ev))

        findings = []
        for val, unit, src in all_values:
            if val is None:
                continue
            ev_ref = _ref(src) if isinstance(src, EvidenceRef) else None
            condition = _range_condition_str(min_val, max_val, strict_min)
            min_violated = (min_val is not None and (val < min_val if not strict_min else val <= min_val))
            max_violated = (max_val is not None and val > max_val)
            if min_violated or max_violated:
                findings.append(ValidationFinding(
                    rule_id=rule_id,
                    category=ValidationCategory.RANGE,
                    status=ValidationStatus.FAIL,
                    severity=severity,
                    field=field_name,
                    description=description,
                    actual_value=val,
                    actual_unit=unit,
                    expected_condition=condition,
                    explanation=(
                        f"Value {val} {unit or ''} is outside the valid range "
                        f"({condition}) for '{field_name}'."
                    ),
                    evidence_refs=[ev_ref] if ev_ref else [],
                ))
        if not findings:
            return [ValidationFinding(
                rule_id=rule_id,
                category=ValidationCategory.RANGE,
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                field=field_name,
                description=description,
                actual_value="(conflicted — see conflict findings)",
                expected_condition=_range_condition_str(min_val, max_val, strict_min),
                explanation=(
                    f"Field '{field_name}' is conflicted but all conflict values "
                    f"are within the valid range ({_range_condition_str(min_val, max_val, strict_min)})."
                ),
            )]
        return findings

    # Single value
    val = nf.canonical_value
    if val is None:
        return [ValidationFinding(
            rule_id=rule_id,
            category=ValidationCategory.RANGE,
            status=ValidationStatus.NOT_CHECKED,
            severity=ValidationSeverity.LOW,
            field=field_name,
            description=description,
            actual_value=None,
            expected_condition=_range_condition_str(min_val, max_val),
            explanation=f"Field '{field_name}' has outcome='{nf.outcome.value}' but no value.",
        )]

    condition = _range_condition_str(min_val, max_val, strict_min)
    min_violated = (min_val is not None and (val < min_val if not strict_min else val <= min_val))
    max_violated = (max_val is not None and val > max_val)
    if min_violated or max_violated:
        return [ValidationFinding(
            rule_id=rule_id,
            category=ValidationCategory.RANGE,
            status=ValidationStatus.FAIL,
            severity=severity,
            field=field_name,
            description=description,
            actual_value=val,
            actual_unit=nf.canonical_unit,
            expected_condition=condition,
            explanation=(
                f"Value {val} {nf.canonical_unit or ''} is outside the valid range "
                f"({condition}) for '{field_name}'."
            ),
            evidence_refs=_refs_from_field(nf),
        )]
    return [ValidationFinding(
        rule_id=rule_id,
        category=ValidationCategory.RANGE,
        status=ValidationStatus.PASS,
        severity=ValidationSeverity.INFO,
        field=field_name,
        description=description,
        actual_value=val,
        actual_unit=nf.canonical_unit,
        expected_condition=condition,
        explanation=(
            f"Field '{field_name}' value {val} {nf.canonical_unit or ''} "
            f"is within the valid range ({condition})."
        ),
        evidence_refs=_refs_from_field(nf),
    )]


def _range_condition_str(min_val: Optional[float], max_val: Optional[float], strict_min: bool = False) -> str:
    if min_val is not None and max_val is not None:
        op = ">" if strict_min else ">="
        return f"{op} {min_val} and <= {max_val}"
    if min_val is not None:
        op = ">" if strict_min else ">="
        return f"{op} {min_val}"
    if max_val is not None:
        return f"<= {max_val}"
    return "any"


def check_range_rated_power(product: NormalizedProduct) -> List[ValidationFinding]:
    """D.1 RANGE_RATED_POWER_POSITIVE — rated_power must be > 0 kW."""
    return _numeric_field_range_check(
        product, "rated_power", _POWER_STRICT_MIN, None,
        "RANGE_RATED_POWER_POSITIVE",
        "rated_power must be positive (> 0 kW)",
        strict_min=True,
    )


def check_range_rated_voltage(product: NormalizedProduct) -> List[ValidationFinding]:
    """D.2 RANGE_RATED_VOLTAGE_POSITIVE — rated_voltage must be > 0 V."""
    return _numeric_field_range_check(
        product, "rated_voltage", _VOLTAGE_STRICT_MIN, None,
        "RANGE_RATED_VOLTAGE_POSITIVE",
        "rated_voltage must be positive (> 0 V)",
        strict_min=True,
    )


def check_range_rated_current(product: NormalizedProduct) -> List[ValidationFinding]:
    """D.3 RANGE_RATED_CURRENT_POSITIVE — rated_current must be > 0 A (if present)."""
    return _numeric_field_range_check(
        product, "rated_current", _CURRENT_STRICT_MIN, None,
        "RANGE_RATED_CURRENT_POSITIVE",
        "rated_current must be positive (> 0 A)",
        strict_min=True,
    )


def check_range_rated_speed(product: NormalizedProduct) -> List[ValidationFinding]:
    """D.4 RANGE_RATED_SPEED_POSITIVE — rated_speed must be > 0 rpm."""
    return _numeric_field_range_check(
        product, "rated_speed", _SPEED_STRICT_MIN, None,
        "RANGE_RATED_SPEED_POSITIVE",
        "rated_speed must be positive (> 0 rpm)",
        strict_min=True,
    )


def check_range_efficiency(product: NormalizedProduct) -> List[ValidationFinding]:
    """D.5 RANGE_EFFICIENCY_BOUNDS — efficiency must be in [0, 100]%."""
    return _numeric_field_range_check(
        product, "efficiency", _EFFICIENCY_MIN_PCT, _EFFICIENCY_MAX_PCT,
        "RANGE_EFFICIENCY_BOUNDS",
        "efficiency must be in [0, 100]%",
        severity=ValidationSeverity.HIGH,
    )


def check_range_power_factor(product: NormalizedProduct) -> List[ValidationFinding]:
    """D.6 RANGE_POWER_FACTOR_BOUNDS — power_factor must be in [0, 1]."""
    return _numeric_field_range_check(
        product, "power_factor", _PF_MIN, _PF_MAX,
        "RANGE_POWER_FACTOR_BOUNDS",
        "power_factor must be in [0.0, 1.0] (dimensionless)",
        severity=ValidationSeverity.HIGH,
    )


def check_range_weight(product: NormalizedProduct) -> List[ValidationFinding]:
    """D.7 RANGE_WEIGHT_POSITIVE — weight must be > 0 kg (if present)."""
    return _numeric_field_range_check(
        product, "weight", _WEIGHT_STRICT_MIN, None,
        "RANGE_WEIGHT_POSITIVE",
        "weight must be positive (> 0 kg)",
        severity=ValidationSeverity.MEDIUM,
        strict_min=True,
    )


# ---------------------------------------------------------------------------
# F. Cross-source consistency validation
# ---------------------------------------------------------------------------

def check_cross_source_consistency(product: NormalizedProduct) -> List[ValidationFinding]:
    """
    F.1 CONSISTENCY_CROSS_SOURCE
    For every field that Phase 2 flagged as 'conflict', surface it as a
    CONFLICT finding with both evidence sources fully preserved.

    This is the core conflict detection logic — Phase 2 already detected the
    disagreement; Phase 3 surfaces it explicitly with provenance and explanation.
    """
    findings = []
    for field_name, nf in product.fields.items():
        if nf.outcome != NormalizationOutcome.CONFLICT:
            continue

        for conflict in nf.conflicts:
            src_a = conflict.source_a
            src_b = conflict.source_b

            findings.append(ValidationFinding(
                rule_id="CONSISTENCY_CROSS_SOURCE",
                category=ValidationCategory.CONFLICT,
                status=ValidationStatus.CONFLICT,
                severity=ValidationSeverity.HIGH,
                field=field_name,
                description=f"Cross-source conflict in '{field_name}'",
                actual_value=f"{conflict.value_a} {conflict.unit_a or ''} vs "
                             f"{conflict.value_b} {conflict.unit_b or ''}",
                expected_condition="all sources should agree on normalized value",
                explanation=(
                    f"CONFLICT: Two sources report different values for '{field_name}' "
                    f"after normalization to canonical units. "
                    f"Source A ({src_a.source_type.upper()}, attr='{src_a.attribute}') "
                    f"reports: {conflict.value_a} {conflict.unit_a or ''} "
                    f"(raw: '{src_a.raw_value}' {src_a.raw_unit or ''}). "
                    f"Source B ({src_b.source_type.upper()}, attr='{src_b.attribute}') "
                    f"reports: {conflict.value_b} {conflict.unit_b or ''} "
                    f"(raw: '{src_b.raw_value}' {src_b.raw_unit or ''}). "
                    f"These two sources disagree about this attribute. "
                    f"No winner has been picked — resolution is deferred to Phase 3 validation."
                ),
                evidence_refs=[r for r in [_ref(src_a), _ref(src_b)] if r],
            ))
    return findings


# ---------------------------------------------------------------------------
# G. Engineering plausibility — Torque/Power/RPM consistency
# ---------------------------------------------------------------------------

def check_engineering_torque_power_rpm(product: NormalizedProduct) -> List[ValidationFinding]:
    """
    G.1 ENGINEERING_TORQUE_POWER_RPM_CONSISTENCY
    Verify mechanical power-torque-speed relationship:
        P = T × ω   where ω = 2π × N / 60
        ⟹ T_expected = (P × 1000 × 60) / (2π × N)    [P in kW → W, N in rpm]

    Tolerance: 15% (see module docstring for justification).

    Data source:
      - P: normalized rated_power (kW) — from NormalizedField (any non-conflict value)
      - N: normalized rated_speed (rpm) — from NormalizedField
      - T: from unmapped_evidence where attribute = 'full_load_torque_nm'

    Note: rated_power is often conflicted between kW column and HP column.
    We use the kW column value (from PDF direct kW extraction) as it is more
    reliable. If all rated_power evidence is conflicted with no agreed value,
    we use the first available parsed value.
    """
    # --- Extract P (rated power in kW) ---
    p_field = product.fields.get("rated_power")
    p_kw: Optional[float] = None
    p_ev_ref: Optional[EvidenceRef] = None

    if p_field is not None:
        if p_field.canonical_value is not None:
            p_kw = float(p_field.canonical_value)
            p_ev_ref = p_field.evidence_refs[0] if p_field.evidence_refs else None
        else:
            # Conflicted — find the kW-column evidence ref (attribute='rated_power')
            for ev in p_field.evidence_refs:
                if ev.parsed_value is not None and ev.raw_unit in ("kW", "kw"):
                    if p_kw is None or abs(ev.parsed_value) < abs(p_kw or 999):
                        p_kw = ev.parsed_value
                        p_ev_ref = ev

    # --- Extract N (rated speed in rpm) ---
    n_field = product.fields.get("rated_speed")
    n_rpm: Optional[float] = None
    n_ev_ref: Optional[EvidenceRef] = None
    if n_field is not None and n_field.canonical_value is not None:
        n_rpm = float(n_field.canonical_value)
        n_ev_ref = n_field.evidence_refs[0] if n_field.evidence_refs else None

    # --- Extract T (torque in Nm from unmapped evidence) ---
    t_nm: Optional[float] = None
    t_ev_ref: Optional[EvidenceRef] = None
    for ev in product.unmapped_evidence:
        if ev.attribute == "full_load_torque_nm" and ev.parsed_value is not None:
            t_nm = ev.parsed_value
            t_ev_ref = ev
            break

    # Build evidence refs list
    ev_refs = [r for r in [_ref(p_ev_ref), _ref(n_ev_ref), _ref(t_ev_ref)] if r]

    # --- Check if we have enough data ---
    if p_kw is None:
        return [ValidationFinding(
            rule_id="ENGINEERING_TORQUE_POWER_RPM",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.NOT_CHECKED,
            severity=ValidationSeverity.LOW,
            field="rated_power",
            description="Torque-Power-RPM consistency check",
            explanation="rated_power has no usable value — engineering check skipped.",
        )]
    if n_rpm is None:
        return [ValidationFinding(
            rule_id="ENGINEERING_TORQUE_POWER_RPM",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.NOT_CHECKED,
            severity=ValidationSeverity.LOW,
            field="rated_speed",
            description="Torque-Power-RPM consistency check",
            explanation="rated_speed has no value — engineering check skipped.",
        )]
    if t_nm is None:
        return [ValidationFinding(
            rule_id="ENGINEERING_TORQUE_POWER_RPM",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.NOT_CHECKED,
            severity=ValidationSeverity.LOW,
            field="full_load_torque_nm",
            description="Torque-Power-RPM consistency check",
            explanation=(
                "No full_load_torque_nm found in unmapped evidence — "
                "Torque-Power-RPM check skipped."
            ),
        )]

    # --- Calculate expected torque ---
    # T_expected = (P_kW × 1000 × 60) / (2π × N_rpm)
    if n_rpm <= 0:
        return [ValidationFinding(
            rule_id="ENGINEERING_TORQUE_POWER_RPM",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.FAIL,
            severity=ValidationSeverity.HIGH,
            field="rated_speed",
            description="Torque-Power-RPM consistency check",
            actual_value=n_rpm,
            actual_unit="rpm",
            expected_condition="> 0",
            explanation=f"rated_speed = {n_rpm} rpm is not positive — cannot compute torque.",
            evidence_refs=ev_refs,
        )]

    t_expected = (p_kw * 1000.0 * 60.0) / (2.0 * math.pi * n_rpm)
    tolerance = _TORQUE_TOL_FRACTION * t_expected
    difference = abs(t_nm - t_expected)
    pct_diff = (difference / t_expected * 100.0) if t_expected != 0 else float("inf")

    if difference <= tolerance:
        return [ValidationFinding(
            rule_id="ENGINEERING_TORQUE_POWER_RPM",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            field="full_load_torque_nm",
            description="Torque-Power-RPM consistency check",
            actual_value=t_nm,
            actual_unit="Nm",
            expected_condition=f"≈ {t_expected:.3f} Nm ± {_TORQUE_TOL_FRACTION*100:.0f}%",
            explanation=(
                f"PASS: Reported torque is consistent with rated power and speed. "
                f"OBSERVED: P={p_kw} kW, N={n_rpm} rpm, T={t_nm} Nm. "
                f"EXPECTED TORQUE: T = (P×1000×60)/(2π×N) = "
                f"({p_kw}×1000×60)/(2π×{n_rpm}) ≈ {t_expected:.3f} Nm. "
                f"DIFFERENCE: {pct_diff:.1f}% (tolerance: {_TORQUE_TOL_FRACTION*100:.0f}%)."
            ),
            evidence_refs=ev_refs,
        )]
    else:
        return [ValidationFinding(
            rule_id="ENGINEERING_TORQUE_POWER_RPM",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.WARNING,
            severity=ValidationSeverity.MEDIUM,
            field="full_load_torque_nm",
            description="Torque-Power-RPM consistency check",
            actual_value=t_nm,
            actual_unit="Nm",
            expected_condition=f"≈ {t_expected:.3f} Nm ± {_TORQUE_TOL_FRACTION*100:.0f}%",
            explanation=(
                f"WARNING: Reported torque deviates from power-speed calculation by {pct_diff:.1f}%. "
                f"OBSERVED: P={p_kw} kW, N={n_rpm} rpm, T={t_nm} Nm. "
                f"EXPECTED TORQUE: T = (P×1000×60)/(2π×N) = "
                f"({p_kw}×1000×60)/(2π×{n_rpm}) ≈ {t_expected:.3f} Nm. "
                f"TOLERANCE: {_TORQUE_TOL_FRACTION*100:.0f}%. "
                "This may be due to measurement conditions or rounding."
            ),
            evidence_refs=ev_refs,
        )]


def check_engineering_efficiency_plausibility(
    product: NormalizedProduct,
) -> List[ValidationFinding]:
    """
    G.2 ENGINEERING_EFFICIENCY_IE3_PLAUSIBILITY
    For IE3 class motors in the 1–15 kW range, full-load efficiency should
    typically be ≥ 80%. This is a warning-level check, not a hard fail.

    Reference: IEC 60034-30-1:2014, IE3 minimum values.
    """
    IE3_MIN_EFFICIENCY = 80.0  # % — conservative floor; actual IE3 minimums are higher

    nf_power = product.fields.get("rated_power")
    nf_eff = product.fields.get("efficiency")

    if nf_eff is None or nf_eff.outcome == NormalizationOutcome.MISSING:
        return [ValidationFinding(
            rule_id="ENGINEERING_EFFICIENCY_IE3",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.NOT_CHECKED,
            severity=ValidationSeverity.LOW,
            field="efficiency",
            description="IE3 efficiency plausibility check",
            explanation="No efficiency value — IE3 check skipped.",
        )]

    # Collect all efficiency values (may be conflicted)
    eff_values = []
    if nf_eff.canonical_value is not None:
        eff_values.append(nf_eff.canonical_value)
    else:
        for c in nf_eff.conflicts:
            if c.value_a is not None:
                eff_values.append(c.value_a)
            if c.value_b is not None:
                eff_values.append(c.value_b)

    findings = []
    for eff in eff_values:
        if eff < IE3_MIN_EFFICIENCY:
            findings.append(ValidationFinding(
                rule_id="ENGINEERING_EFFICIENCY_IE3",
                category=ValidationCategory.ENGINEERING,
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.MEDIUM,
                field="efficiency",
                description="IE3 efficiency plausibility check",
                actual_value=eff,
                actual_unit="%",
                expected_condition=f"≥ {IE3_MIN_EFFICIENCY}% for IE3 class",
                explanation=(
                    f"Efficiency value {eff}% is below the typical IE3 floor of "
                    f"{IE3_MIN_EFFICIENCY}%. This may indicate a different load "
                    f"point (e.g. 50% load) or a non-IE3 product. "
                    "Review the evidence source for context."
                ),
                evidence_refs=_refs_from_field(nf_eff),
            ))
        else:
            findings.append(ValidationFinding(
                rule_id="ENGINEERING_EFFICIENCY_IE3",
                category=ValidationCategory.ENGINEERING,
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                field="efficiency",
                description="IE3 efficiency plausibility check",
                actual_value=eff,
                actual_unit="%",
                expected_condition=f"≥ {IE3_MIN_EFFICIENCY}%",
                explanation=(
                    f"Efficiency {eff}% is plausible for an IE3 class motor "
                    f"(≥ {IE3_MIN_EFFICIENCY}% threshold)."
                ),
                evidence_refs=_refs_from_field(nf_eff),
            ))
    return findings if findings else [ValidationFinding(
        rule_id="ENGINEERING_EFFICIENCY_IE3",
        category=ValidationCategory.ENGINEERING,
        status=ValidationStatus.NOT_CHECKED,
        severity=ValidationSeverity.LOW,
        field="efficiency",
        description="IE3 efficiency plausibility check",
        explanation="No efficiency values found after normalization.",
    )]


def check_engineering_synchronous_speed(product: NormalizedProduct) -> List[ValidationFinding]:
    """
    G.3 ENGINEERING_SYNCHRONOUS_SPEED
    Verify that rated_speed < synchronous speed (ns).
    ns = 120 × f / poles
    A motor's rotor always runs slightly below synchronous speed (slip > 0).

    If poles can be inferred from the product_id pattern (e.g. '4P' → 4 poles),
    use that. If frequency is missing, assume 50 Hz (standard for WEG European spec).

    This check uses inference conservatively — if we cannot safely infer,
    we skip the check and document why.
    """
    # Try to get rated speed
    n_field = product.fields.get("rated_speed")
    if n_field is None or n_field.canonical_value is None:
        return [ValidationFinding(
            rule_id="ENGINEERING_SYNCHRONOUS_SPEED",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.NOT_CHECKED,
            severity=ValidationSeverity.LOW,
            field="rated_speed",
            description="Synchronous speed consistency check",
            explanation="rated_speed has no value — synchronous speed check skipped.",
        )]
    n_rpm = float(n_field.canonical_value)

    # Try to infer poles from product_id  (e.g. "PIQ-W22SP-4P-1.1" → 4)
    poles: Optional[int] = None
    pid = product.product_id
    for suffix in ["2P", "4P", "6P", "8P"]:
        if suffix in pid:
            poles = int(suffix[:-1])
            break

    # Also try the poles field
    if poles is None:
        p_field = product.fields.get("poles")
        if p_field is not None and p_field.canonical_value is not None:
            try:
                poles = int(p_field.canonical_value)
            except (TypeError, ValueError):
                pass

    if poles is None:
        return [ValidationFinding(
            rule_id="ENGINEERING_SYNCHRONOUS_SPEED",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.NOT_CHECKED,
            severity=ValidationSeverity.LOW,
            field="poles",
            description="Synchronous speed consistency check",
            explanation=(
                "Cannot determine pole count from product_id or poles field — "
                "synchronous speed check skipped."
            ),
        )]

    # Frequency: use 50 Hz if not available (WEG European spec)
    frequency: float = 50.0
    f_field = product.fields.get("frequency")
    if f_field is not None and f_field.canonical_value is not None:
        frequency = float(f_field.canonical_value)
    freq_note = "" if (f_field and f_field.canonical_value) else " (assumed 50 Hz — WEG European spec)"

    ns = 120.0 * frequency / poles  # synchronous speed in rpm
    slip = (ns - n_rpm) / ns

    ev_refs = []
    if n_field.evidence_refs:
        ev_refs.append(_ref(n_field.evidence_refs[0]))

    if n_rpm <= 0:
        return [ValidationFinding(
            rule_id="ENGINEERING_SYNCHRONOUS_SPEED",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.FAIL,
            severity=ValidationSeverity.HIGH,
            field="rated_speed",
            description="Synchronous speed consistency check",
            actual_value=n_rpm,
            actual_unit="rpm",
            expected_condition=f"< synchronous speed ({ns:.0f} rpm)",
            explanation=f"rated_speed = {n_rpm} rpm is not positive.",
            evidence_refs=[r for r in ev_refs if r],
        )]

    if n_rpm >= ns:
        return [ValidationFinding(
            rule_id="ENGINEERING_SYNCHRONOUS_SPEED",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.FAIL,
            severity=ValidationSeverity.HIGH,
            field="rated_speed",
            description="Synchronous speed consistency check",
            actual_value=n_rpm,
            actual_unit="rpm",
            expected_condition=f"< {ns:.0f} rpm (synchronous speed for {poles}-pole, {frequency} Hz)",
            explanation=(
                f"FAIL: rated_speed ({n_rpm} rpm) ≥ synchronous speed ({ns:.0f} rpm). "
                f"An induction motor's rotor must run below synchronous speed (slip > 0). "
                f"ns = 120 × {frequency} / {poles} = {ns:.0f} rpm{freq_note}."
            ),
            evidence_refs=[r for r in ev_refs if r],
        )]

    if slip < 0.001:
        # Suspiciously close to synchronous speed — warn
        return [ValidationFinding(
            rule_id="ENGINEERING_SYNCHRONOUS_SPEED",
            category=ValidationCategory.ENGINEERING,
            status=ValidationStatus.WARNING,
            severity=ValidationSeverity.LOW,
            field="rated_speed",
            description="Synchronous speed consistency check",
            actual_value=n_rpm,
            actual_unit="rpm",
            expected_condition=f"< {ns:.0f} rpm (reasonable slip > 0.1%)",
            explanation=(
                f"rated_speed ({n_rpm} rpm) is within 0.1% of synchronous speed "
                f"({ns:.0f} rpm). Slip = {slip*100:.2f}%. "
                "This is unusually low for an induction motor — verify the speed value."
            ),
            evidence_refs=[r for r in ev_refs if r],
        )]

    return [ValidationFinding(
        rule_id="ENGINEERING_SYNCHRONOUS_SPEED",
        category=ValidationCategory.ENGINEERING,
        status=ValidationStatus.PASS,
        severity=ValidationSeverity.INFO,
        field="rated_speed",
        description="Synchronous speed consistency check",
        actual_value=n_rpm,
        actual_unit="rpm",
        expected_condition=f"< {ns:.0f} rpm (synchronous speed for {poles}-pole, {frequency} Hz)",
        explanation=(
            f"PASS: rated_speed ({n_rpm} rpm) < synchronous speed ({ns:.0f} rpm). "
            f"Slip = {slip*100:.2f}%. "
            f"ns = 120 × {frequency} / {poles} = {ns:.0f} rpm{freq_note}."
        ),
        evidence_refs=[r for r in ev_refs if r],
    )]


# ---------------------------------------------------------------------------
# I. Conflict detection — explicit surfacing of Phase 2 conflicts
# ---------------------------------------------------------------------------

def check_known_current_conflict(product: NormalizedProduct) -> List[ValidationFinding]:
    """
    I.1 CONFLICT_RATED_CURRENT_PDF_VS_CSV
    Specifically detect and surface the known PDF (2.34 A) vs CSV (7.22 A)
    conflict in rated_current. This is a hard-gate demo requirement.

    The conflict is detected by looking for the specific attribute pattern:
      - source_a.source_type = 'pdf', attribute = 'rated_current'
      - source_b.source_type = 'csv', attribute = 'rated_current'
      - values differ significantly
    """
    nf = product.fields.get("rated_current")
    if nf is None:
        return []

    findings = []
    for conflict in nf.conflicts:
        src_a = conflict.source_a
        src_b = conflict.source_b

        # Check for the PDF/CSV current discrepancy
        pdf_src = None
        csv_src = None
        pdf_val = None
        csv_val = None

        if src_a.source_type == "pdf" and src_b.source_type == "csv":
            pdf_src, csv_src = src_a, src_b
            pdf_val, csv_val = conflict.value_a, conflict.value_b
        elif src_b.source_type == "pdf" and src_a.source_type == "csv":
            pdf_src, csv_src = src_b, src_a
            pdf_val, csv_val = conflict.value_b, conflict.value_a

        if pdf_src is not None and csv_src is not None:
            findings.append(ValidationFinding(
                rule_id="CONFLICT_RATED_CURRENT_PDF_VS_CSV",
                category=ValidationCategory.CONFLICT,
                status=ValidationStatus.CONFLICT,
                severity=ValidationSeverity.HIGH,
                field="rated_current",
                description=(
                    "PDF-reported rated current conflicts with CSV-reported value"
                ),
                actual_value=(
                    f"PDF: {pdf_val} A (raw: '{pdf_src.raw_value}') vs "
                    f"CSV: {csv_val} A (raw: '{csv_src.raw_value}')"
                ),
                expected_condition="all sources should report the same rated current",
                explanation=(
                    f"CONFLICT: These two sources disagree about rated_current. "
                    f"PDF source ('{pdf_src.attribute}') reports {pdf_val} A "
                    f"(raw: '{pdf_src.raw_value}'). "
                    f"CSV source ('{csv_src.attribute}') reports {csv_val} A "
                    f"(raw: '{csv_src.raw_value}'). "
                    f"NOTE: The CSV column 'full_load_current_a' contains the value "
                    f"{csv_val}, which matches the full-load torque in Nm from the PDF. "
                    f"This suggests the CSV column may be mislabeled as current when "
                    f"it actually contains torque data. "
                    f"Resolution requires Phase 3 cross-field consistency analysis. "
                    f"No winner has been picked — both values are preserved."
                ),
                evidence_refs=[r for r in [_ref(pdf_src), _ref(csv_src)] if r],
            ))

    return findings
