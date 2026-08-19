# ProductIQ Validation Engine — Technical Reference

## Overview

The ProductIQ validation engine is the Phase 3 component of the intelligence pipeline. It applies deterministic, explainable, offline-capable rules to `NormalizedProduct` instances from Phase 2 and produces `ProductValidationReport` instances containing structured `ValidationFinding` records.

**Design principles:**
- **Deterministic** — same input always produces identical output
- **Explainable** — every finding includes a human-readable explanation referencing observed values, expected conditions, and evidence provenance
- **Offline-capable** — no network access, no LLM, no external services required
- **Non-destructive** — validation never modifies normalized values or discards evidence
- **Provenance-preserving** — every finding carries `FindingEvidenceRef` records linking back to original sources

---

## Module Structure

```
productiq/validation/
    __init__.py          — public API exports
    base.py              — BaseValidator abstract interface (Phase 0 stub, preserved)
    models.py            — ValidationFinding, ProductValidationReport, enums
    rules.py             — all validation rule functions (modular, one function per rule)
    validator.py         — MotorValidator, BatchValidator (orchestrators)
```

---

## Data Model

### ValidationStatus (Enum)

| Value | Meaning |
|---|---|
| `PASS` | Check passed — no issues found |
| `WARNING` | Minor issue — product is usable but attention needed |
| `CONFLICT` | Two sources disagree after normalization to canonical units |
| `FAIL` | Serious issue — range violation, schema error, or physics contradiction |
| `NOT_CHECKED` | Check skipped due to missing data — not an error for optional fields |

### ValidationSeverity (Enum)

| Value | Meaning |
|---|---|
| `INFO` | Informational — no action needed |
| `LOW` | Low impact — worth noting |
| `MEDIUM` | Medium impact — should be reviewed |
| `HIGH` | High impact — needs resolution before production use |
| `CRITICAL` | Critical — product intelligence is unreliable |

### ValidationCategory (Enum)

| Value | Category |
|---|---|
| `SCHEMA` | A. Schema conformance |
| `REQUIRED_FIELD` | B. Required field presence |
| `TYPE` | C. Type correctness |
| `RANGE` | D. Range / plausibility |
| `UNIT` | E. Unit / canonical consistency |
| `CONSISTENCY` | F. Cross-source consistency |
| `ENGINEERING` | G. Engineering relationship plausibility |
| `MISSING_DATA` | H. Missing data completeness |
| `CONFLICT` | I. Detected evidence conflict |

### ValidationFinding

Every finding records:

| Field | Type | Description |
|---|---|---|
| `rule_id` | str | Unique rule identifier (e.g. `RANGE_RATED_POWER_POSITIVE`) |
| `category` | ValidationCategory | Which validation category this belongs to |
| `status` | ValidationStatus | PASS / WARNING / CONFLICT / FAIL / NOT_CHECKED |
| `severity` | ValidationSeverity | INFO / LOW / MEDIUM / HIGH / CRITICAL |
| `field` | str | Canonical field name (e.g. `rated_current`) |
| `description` | str | Short human-readable rule description |
| `actual_value` | Any | Value that was checked |
| `actual_unit` | str | Unit of actual_value |
| `expected_condition` | str | Expected condition (e.g. `> 0`) |
| `explanation` | str | Full human-readable explanation |
| `evidence_refs` | List[FindingEvidenceRef] | Provenance links to original sources |

### ProductValidationReport

Contains:
- `product_id`, `manufacturer`, `model` — identity
- `overall_status` — worst status across all findings
- `findings` — list of ValidationFinding
- `summary` — counts by status
- `findings_by_category` — counts by category

---

## Rule Engine

### Rule Naming Convention

```
<CATEGORY>_<FIELD>_<CHECK>
```

Examples:
- `RANGE_RATED_POWER_POSITIVE`
- `CONSISTENCY_CROSS_SOURCE`
- `ENGINEERING_TORQUE_POWER_RPM`
- `CONFLICT_RATED_CURRENT_PDF_VS_CSV`

### Rule Application Order

```python
# A. Schema
check_schema_canonical_units(product)
check_schema_normalization_version(product)

# B. Required / Important Fields
check_required_fields(product)
check_important_fields(product)

# D. Range
check_range_rated_power(product)
check_range_rated_voltage(product)
check_range_rated_current(product)
check_range_rated_speed(product)
check_range_efficiency(product)
check_range_power_factor(product)
check_range_weight(product)

# F. Cross-source Consistency
check_cross_source_consistency(product)

# G. Engineering
check_engineering_torque_power_rpm(product)
check_engineering_efficiency_plausibility(product)
check_engineering_synchronous_speed(product)

# H. Missing Data
check_missing_data_inventory(product)

# I. Known Conflicts
check_known_current_conflict(product)
```

---

## Validation Rules Reference

### A. Schema Rules

#### `SCHEMA_CANONICAL_UNITS`
- **Category:** SCHEMA
- **Condition:** `field.canonical_unit == CANONICAL_UNITS[field_name]`
- **Severity:** HIGH (FAIL), INFO (PASS)
- **Purpose:** Ensures Phase 2 did not produce fields with incorrect unit annotations relative to Phase 0 registry.

#### `SCHEMA_NORMALIZATION_VERSION`
- **Category:** SCHEMA
- **Condition:** `normalization_version == "2.0.0"`
- **Severity:** LOW (WARNING), INFO (PASS)
- **Purpose:** Guards against accidentally validating products from a different normalization run.

---

### B. Required-Field Rules

#### `REQUIRED_FIELD_PRESENCE`
- **Category:** REQUIRED_FIELD
- **Required fields:** `rated_power`, `rated_voltage`, `rated_speed`
- **Condition:** field must have at least one evidence record (not MISSING outcome)
- **Severity:** HIGH (FAIL)
- **Rationale:** These three fields are the minimum needed to characterize a motor. A product missing all three cannot be safely used in any application.

#### `IMPORTANT_FIELD_PRESENCE`
- **Category:** MISSING_DATA
- **Important fields:** `rated_current`, `efficiency`, `weight`
- **Condition:** field should have evidence
- **Severity:** MEDIUM (WARNING)
- **Rationale:** Important for full characterization but not required for basic motor identification.

---

### D. Range Rules

All range rules use the following severity model:
- Single value out of range → FAIL (HIGH)
- Conflicted field with all values in range → PASS
- Conflicted field with some values out of range → FAIL (per violating value)
- Missing field → NOT_CHECKED (LOW)

| Rule ID | Field | Condition | Justification |
|---|---|---|---|
| `RANGE_RATED_POWER_POSITIVE` | rated_power | > 0 kW | Power cannot be zero or negative (motors produce output) |
| `RANGE_RATED_VOLTAGE_POSITIVE` | rated_voltage | > 0 V | Voltage is a physical quantity > 0 |
| `RANGE_RATED_CURRENT_POSITIVE` | rated_current | > 0 A | Full-load current must be positive |
| `RANGE_RATED_SPEED_POSITIVE` | rated_speed | > 0 rpm | Rotating machinery has positive speed |
| `RANGE_EFFICIENCY_BOUNDS` | efficiency | [0, 100]% | Physical bounds on efficiency |
| `RANGE_POWER_FACTOR_BOUNDS` | power_factor | [0.0, 1.0] | Physical bounds on power factor |
| `RANGE_WEIGHT_POSITIVE` | weight | > 0 kg | Physical mass is positive |

---

### F. Cross-Source Consistency

#### `CONSISTENCY_CROSS_SOURCE`
- **Category:** CONFLICT
- **Condition:** If `NormalizedField.outcome == CONFLICT`, surface a CONFLICT finding
- **Severity:** HIGH
- **Evidence:** Both `source_a` and `source_b` from every `ConflictRecord` are preserved as `FindingEvidenceRef`
- **Output format:**
  ```
  CONFLICT: Two sources report different values for 'rated_current' after
  normalization to canonical units.
  Source A (PDF, attr='rated_current') reports: 2.34 A (raw: '2.34' A).
  Source B (CSV, attr='rated_current') reports: 7.22 A (raw: '7.22' A).
  These two sources disagree about this attribute.
  No winner has been picked — resolution is deferred to Phase 3 validation.
  ```

---

### G. Engineering Rules

#### `ENGINEERING_TORQUE_POWER_RPM`
- **Category:** ENGINEERING
- **Formula:** `T_expected = (P_kW × 1000 × 60) / (2π × N_rpm)` [Nm]
- **Tolerance:** ±15% of expected torque
- **Data sources:**
  - P: `rated_power` field (uses kW-unit evidence ref if conflicted)
  - N: `rated_speed` field
  - T: `unmapped_evidence` where `attribute == "full_load_torque_nm"`
- **Justification for 15% tolerance:** Manufacturer tables round values; shaft efficiency varies with temperature and load; measurement conditions differ between PDF specification and CSV test data.

**Example (PIQ-W22SP-4P-1.1):**
```
P = 1.1 kW, N = 1455 rpm
T_expected = (1.1 × 1000 × 60) / (2π × 1455) = 7.219 Nm
T_reported = 7.22 Nm
Difference = 0.0% → PASS
```

#### `ENGINEERING_EFFICIENCY_IE3`
- **Category:** ENGINEERING
- **Condition:** efficiency ≥ 80% (warning threshold, not hard fail)
- **Reference:** IEC 60034-30-1:2014, IE3 minimum efficiency class
- **Rationale:** WEG W22 Severe Process is advertised as IE3 class. Efficiency < 80% at rated load would be surprising. The warning allows for partial-load test data, which can show lower efficiency.

#### `ENGINEERING_SYNCHRONOUS_SPEED`
- **Category:** ENGINEERING
- **Formula:** `n_s = 120 × f / poles` [rpm]
- **Condition:** `rated_speed < n_s` (slip must be > 0 for induction motors)
- **Pole inference:** Extracted from `product_id` suffix (`4P` → 4, `6P` → 6)
- **Frequency assumption:** 50 Hz if `frequency` field is missing (WEG European specification)

**Example (PIQ-W22SP-4P-1.1):**
```
poles = 4 (from "4P" in product_id)
n_s = 120 × 50 / 4 = 1500 rpm
rated_speed = 1455 rpm
slip = (1500 - 1455) / 1500 = 3.0% → PASS
```

---

### H. Missing-Data Inventory

#### `MISSING_DATA_INVENTORY`
- **Category:** MISSING_DATA
- **Status:** NOT_CHECKED
- **Purpose:** Honest accounting of optional fields with no evidence. Not an error — it is important to distinguish "we checked and it passed" from "we could not check".

---

### I. Known Conflict Detection

#### `CONFLICT_RATED_CURRENT_PDF_VS_CSV`
- **Category:** CONFLICT
- **Status:** CONFLICT (when detected)
- **Severity:** HIGH
- **Trigger:** `rated_current` conflict where one source is PDF and one is CSV
- **Purpose:** Specifically surfaces the documented real-world data quality issue where CSV `full_load_current_a = 7.22` appears to be mislabeled — the value matches the full-load torque (7.22 Nm from PDF) rather than the rated current (2.34 A from PDF).
- **Output:** The explanation explicitly notes the mislabeling hypothesis and preserves both raw values.

---

## Conflict Handling Philosophy

Phase 3 does **not** resolve conflicts. This is intentional.

Phase 2 detected disagreements between sources. Phase 3 surfaces these as `CONFLICT` findings with full provenance. The production resolution would occur in:
- Phase 4 (Enrichment) — LLM reasoning with citation requirements
- Phase 5 (Trust Scoring) — source authority and quality scoring

Every conflict finding carries:
1. **WHAT** — which attribute is in conflict
2. **VALUE A + SOURCE A** — first evidence value and its provenance
3. **VALUE B + SOURCE B** — second evidence value and its provenance
4. **WHY** — why they disagree after normalization
5. **SEVERITY** — impact level

---

## Provenance Chain

```
Original Source (PDF/CSV/Web)
        ↓
EvidenceRecord [Phase 1]
  (attribute, raw_value, page, row, column, url)
        ↓
EvidenceRef [Phase 2]
  (source_id, source_type, raw_value, raw_unit, parsed_value, page, row)
        ↓
FindingEvidenceRef [Phase 3]
  (source_id, source_type, attribute, raw_value, raw_unit, page, row, section)
```

At every stage, the original raw value is preserved verbatim. Validation can always trace back to the exact character strings extracted from the original sources.

---

## Failure Handling

| Condition | Behavior |
|---|---|
| Normalized product file missing | `BatchValidator` logs error, marks product as failed, continues |
| Field with no evidence | `NOT_CHECKED` finding returned, not a crash |
| Field with conflict | CONFLICT findings generated for each `ConflictRecord` |
| Engineering check data missing | `NOT_CHECKED` finding with explanation |
| Exception in rule function | Rule exception propagates — do not hide failures |

---

## Offline Capability

Phase 3 has **zero network dependencies**:
- No HTTP requests
- No LLM API calls
- No database connections
- No external file reads beyond the local data directory

All validation logic is pure Python using `math`, `json`, and the local `productiq` package.

---

## Representative Examples

### Example 1: Consistent Cross-Source (PASS)

```
RULE: CONSISTENCY_CROSS_SOURCE (no finding — both sources agree)
RULE: RANGE_RATED_VOLTAGE_POSITIVE
STATUS: PASS
FIELD: rated_voltage
OBSERVED: 400.0 V (PDF and CSV both report 400 V)
EXPLANATION: Field 'rated_voltage' value 400.0 V is within the valid range (>= 0).
```

### Example 2: Known Conflict (CONFLICT)

```
RULE: CONFLICT_RATED_CURRENT_PDF_VS_CSV
STATUS: CONFLICT
SEVERITY: HIGH
FIELD: rated_current
OBSERVED: PDF: 2.34 A vs CSV: 7.22 A
EXPLANATION:
  CONFLICT: These two sources disagree about rated_current.
  PDF source ('rated_current') reports 2.34 A (raw: '2.34').
  CSV source ('rated_current') reports 7.22 A (raw: '7.22').
  NOTE: The CSV column 'full_load_current_a' contains the value 7.22, which
  matches the full-load torque in Nm from the PDF. This suggests the CSV column
  may be mislabeled as current when it actually contains torque data.
  No winner has been picked — both values are preserved.
EVIDENCE REFS:
  [0] source_type=pdf, attribute=rated_current, raw_value=2.34
  [1] source_type=csv, attribute=rated_current, raw_value=7.22
```

### Example 3: Engineering Check (PASS)

```
RULE: ENGINEERING_TORQUE_POWER_RPM
STATUS: PASS
FIELD: full_load_torque_nm
OBSERVED: P=1.1 kW, N=1455 rpm, T=7.22 Nm
EXPECTED TORQUE: T = (P×1000×60)/(2π×N) = (1.1×1000×60)/(2π×1455) ≈ 7.219 Nm
DIFFERENCE: 0.0% (tolerance: 15%)
```
