# ProductIQ Normalization — Technical Reference

## Overview

The normalization layer (Phase 2) transforms raw `EvidenceRecord` observations from Phase 1 into structured `NormalizedProduct` objects with:

- **Canonical units** (kW, V, A, Hz, rpm, kg, %)
- **Full provenance** traceable to every original source
- **Explicit conflict surfacing** — no silent winner-picking
- **Deterministic behavior** — identical input always produces identical output
- **No LLM dependency** — all conversions are pure math

---

## Evidence Loading

Evidence is loaded from JSON files written by Phase 1 extraction:

```
data/processed/<product_id>/pdf_evidence.json   # PDF brochure evidence
data/processed/<product_id>/csv_evidence.json   # CSV catalog evidence
data/processed/<product_id>/web_evidence.json   # Web evidence (HTTP 403 for WEG)
data/processed/GLOBAL/pdf_evidence.json         # Global constants (voltage)
```

Each file contains an `ExtractionResult` dict with an `evidence` list. If a file is `status: "failed"` (e.g., web evidence blocked by HTTP 403), it yields zero evidence records — normalization gracefully handles zero evidence as `Missing`.

### Code

```python
from productiq.normalization import MotorNormalizer
from pathlib import Path

normalizer = MotorNormalizer(data_dir=Path("data"))
evidence = normalizer.load_all_evidence("PIQ-W22SP-4P-1.1")
# → list of dict, each representing one EvidenceRecord
```

---

## Attribute Mapping

Every `EvidenceRecord.attribute` is classified against an explicit mapping table in `attribute_mapper.py`:

| Kind | Description | Example attributes |
|---|---|---|
| `CANONICAL` | Maps to a Phase 0 `MotorProduct` field | `rated_power`, `rated_power_hp`, `full_load_current_a` |
| `METADATA` | Auxiliary column — excluded from normalization | `rated_power_unit`, `current_unit` |
| `UNMAPPED` | No canonical field — preserved in `unmapped_evidence` | `full_load_torque_nm`, `inertia_kgm2`, `sound_dba` |
| `SKIP` | Intentionally excluded (source reference text) | `source_location` |

### Multiple attributes → same canonical field

Multiple evidence attributes can map to the same canonical field:

```
rated_power       (kW)  ─┐
rated_power_kw    (kW)  ──┼─► MotorProduct.rated_power (canonical: kW)
rated_power_hp    (HP)  ─┘
rated_power_raw   (str) ─┘
```

When these produce different normalized values (e.g. 1.1 kW vs 1.11855 kW from HP conversion), the conflict is preserved rather than resolved.

### Code

```python
from productiq.normalization.attribute_mapper import get_mapping, MappingKind

canonical_field, kind, note = get_mapping("rated_power_hp")
# canonical_field = "rated_power"
# kind = MappingKind.CANONICAL
# note = "Power in HP → convert to kW"
```

---

## Value Parsing

Raw values from `EvidenceRecord.raw_value` are parsed by `value_parser.py`. The parser is conservative: it handles realistic manufacturer formatting variation but never guesses a value from an unrecognizable format.

### Supported formats

| Pattern | Example | Result |
|---|---|---|
| Plain numeric | `"1.1"` | `(1.1, None)` |
| Numeric + unit | `"1.1 kW"` | `(1.1, "kW")` |
| Percentage | `"84.8 %"` | `(84.8, "%")` |
| Percentage no-space | `"84.8%"` | `(84.8, "%")` |
| HP value | `"1.5 HP"` | `(1.5, "HP")` |
| Integer | `"1455"` | `(1455.0, None)` |
| Scientific notation | `"1.1e3"` | `(1100.0, None)` |
| IP rating | `"IP56"`, `"56"`, `"IP56+ sealing..."` | `"IP56"` |
| Frame size | `"90S"`, `"L90S"` | `"90S"` / `"L90S"` |

### Failure behavior

Malformed values raise `ValueParseError` — they are captured as `NormalizationIssue` records and never silently dropped or replaced with a fabricated value.

### Code

```python
from productiq.normalization.value_parser import parse_numeric, ValueParseError

try:
    value, unit = parse_numeric("1.1 kW")
    # → (1.1, "kW")
except ValueParseError as e:
    # handle gracefully — never guess
```

---

## Unit Conversion

All unit conversions in `unit_converter.py` use exact physical constants. No approximations.

### Conversion table

| Source unit | Canonical unit | Factor | Field(s) |
|---|---|---|---|
| W (watt) | kW | × 0.001 | `rated_power` |
| HP (horsepower) | kW | × 0.7457 (IEC) | `rated_power` |
| mW (milliwatt) | kW | × 0.000001 | `rated_power` |
| g (gram) | kg | × 0.001 | `weight` |
| lb (pound) | kg | × 0.453592 | `weight` |
| fraction [0,1] | % | × 100 | `efficiency` |
| % (efficiency) | % | passthrough | `efficiency` |
| % (power factor) | fraction | ÷ 100 | `power_factor` |
| fraction (PF) | fraction | passthrough | `power_factor` |
| V, A, Hz, rpm | same | passthrough | respective fields |

### Unit alias normalization

Unit strings are normalized case-insensitively before conversion:

```
"kw"  → "kW"     "KW"      → "kW"
"hp"  → "HP"     "horsepower" → "HP"
"r/min" → "rpm"  "rev/min"  → "rpm"
"kilogram" → "kg"
```

Unknown units raise `UnitConversionError` — they are never silently mapped to a canonical unit.

### Code

```python
from productiq.normalization.unit_converter import convert_value, UnitConversionError

# 1100 W → 1.1 kW
value, unit = convert_value("rated_power", 1100.0, "W")
# → (1.1, "kW")

# 1.5 HP → 1.11855 kW
value, unit = convert_value("rated_power", 1.5, "HP")
# → (1.11855, "kW")

# 19500 g → 19.5 kg
value, unit = convert_value("weight", 19500.0, "g")
# → (19.5, "kg")
```

---

## Canonicalization and FieldValue Construction

After value parsing and unit conversion, each evidence record produces a `_NormResult` containing:

```python
@dataclass
class _NormResult:
    canonical_field: str         # e.g. "rated_power"
    canonical_value: Any         # normalized value (float or str)
    canonical_unit: Optional[str] # e.g. "kW"
    evidence_ref: EvidenceRef    # full provenance pointer
    outcome: NormalizationOutcome
```

These are accumulated per canonical field and assembled into a `NormalizedField`.

---

## Provenance

Every `EvidenceRef` in a `NormalizedField.evidence_refs` carries:

| Field | Meaning |
|---|---|
| `source_id` | Stable document identifier (e.g. `"WEG_W22_Severe_Process_IE3_Brochure"`) |
| `source_type` | `"pdf"`, `"csv"`, or `"web"` |
| `product_id` | ProductIQ product ID |
| `attribute` | **Original evidence attribute name** (before mapping) |
| `raw_value` | **Exact string from the source** (never modified) |
| `raw_unit` | Unit as found in source |
| `parsed_value` | Float parsed from `raw_value` |
| `page` | PDF page number (or `null`) |
| `row` | CSV row number (or `null`) |
| `column` | CSV column name (or `null`) |
| `url` | Web URL (or `null`) |
| `section` | Section heading context (or `null`) |
| `method` | Extraction method (`table`, `column`, etc.) |
| `confidence` | Phase 1 extraction confidence [0.0, 1.0] |

**Invariant:** raw values are never modified. The string `"7.22"` in `raw_value` is exactly what appeared in the CSV cell — not rounded, not converted, not replaced.

---

## Conflict Preservation

When two evidence sources produce different normalized values for the same canonical field, both are preserved in a `ConflictRecord`:

```python
@dataclass
class ConflictRecord:
    canonical_field: str
    value_a: Optional[float]    # First normalized value
    unit_a:  Optional[str]
    source_a: EvidenceRef       # Full provenance of value_a

    value_b: Optional[float]    # Second normalized value (different from value_a)
    unit_b:  Optional[str]
    source_b: EvidenceRef       # Full provenance of value_b

    note: str                   # Human-readable description
```

When conflicts exist, `NormalizedField.canonical_value = None` — Phase 2 never picks a winner.

### Real example: rated_current for PIQ-W22SP-4P-1.1

```json
{
  "canonical_field": "rated_current",
  "canonical_value": null,
  "outcome": "conflict",
  "conflicts": [
    {
      "value_a": 2.34,
      "unit_a": "A",
      "source_a": {
        "source_type": "pdf",
        "attribute": "rated_current",
        "raw_value": "2.34",
        "page": 5
      },
      "value_b": 7.22,
      "unit_b": "A",
      "source_b": {
        "source_type": "csv",
        "attribute": "rated_current",
        "raw_value": "7.22",
        "column": "full_load_current_a"
      },
      "note": "Numeric conflict: 2.34 A vs 7.22 A"
    }
  ]
}
```

The CSV value `7.22` is preserved verbatim — the column `full_load_current_a` actually contains torque data (Nm) rather than current. This is a known data quality issue documented to be resolved by Phase 3 validation logic.

---

## Missing Data

If no evidence exists for a canonical field, the field is represented as `Missing` — never guessed or inferred:

```json
{
  "canonical_field": "frequency",
  "canonical_value": null,
  "outcome": "missing",
  "evidence_refs": [],
  "confidence": null,
  "notes": ["No evidence available for this field."]
}
```

The missing `frequency` field is a known limitation of Phase 1 extraction scope (see `docs/PHASE_2.md` for details).

---

## Equivalent Value Reconciliation

When multiple sources agree after normalization, all evidence references are preserved and a single canonical value is returned:

```
PDF "19.5 kg" → passthrough → 19.5 kg
CSV "19.5 kg" → passthrough → 19.5 kg
───────────────────────────────────────
canonical_value = 19.5 (both refs preserved, outcome = passthrough)
```

The `evidence_refs` list contains all contributing EvidenceRef records, so downstream consumers can see how many sources agreed.

---

## Error Handling

| Error class | When raised | What happens |
|---|---|---|
| `ValueParseError` | Raw string cannot be parsed as numeric/string | Captured as `NormalizationIssue(outcome=PARSE_ERROR)` — field gets no value |
| `UnitConversionError` | Unit string not recognized or no conversion rule | Captured as `NormalizationIssue(outcome=UNKNOWN_UNIT)` — field gets no value |

Neither error type causes a crash. Both are surfaced in `NormalizedProduct.issues` for audit.

---

## Normalization Outcomes

| Outcome | Meaning |
|---|---|
| `normalized` | Value was converted from a non-canonical unit to canonical unit (e.g. HP → kW) |
| `passthrough` | Value was already in canonical unit — no conversion needed |
| `conflict` | Multiple evidence values disagree — no winner picked |
| `missing` | No evidence available for this field |
| `parse_error` | Raw value string could not be parsed |
| `unknown_unit` | Unit present but not recognized |
| `unmapped` | Evidence attribute has no canonical field mapping |

---

## Examples

### Example 1: 1100 W → 1.1 kW (unit conversion with provenance)

**Evidence input:**
```json
{
  "attribute": "rated_power",
  "raw_value": "1100",
  "value": 1100.0,
  "unit": "W",
  "source_type": "pdf",
  "page": 5
}
```

**Normalization:**
1. `get_mapping("rated_power")` → `CANONICAL`, maps to `rated_power`
2. `parse_numeric("1100")` → `(1100.0, None)` — use `unit="W"` from EvidenceRecord
3. `convert_value("rated_power", 1100.0, "W")` → `(1.1, "kW")` (factor: × 0.001)
4. Build `EvidenceRef` with `raw_value="1100"`, `raw_unit="W"`, `parsed_value=1100.0`

**NormalizedField output:**
```json
{
  "canonical_field": "rated_power",
  "canonical_unit": "kW",
  "canonical_value": 1.1,
  "outcome": "normalized",
  "evidence_refs": [{
    "raw_value": "1100",
    "raw_unit": "W",
    "parsed_value": 1100.0
  }]
}
```

### Example 2: Preserved conflict (PDF 2.34 A vs CSV 7.22 A)

**Evidence inputs:**
```
PDF: rated_current = "2.34" A  (page 5, table row)
CSV: full_load_current_a = "7.22" A  (row 1, column full_load_current_a)
```

**After normalization:**
- PDF 2.34 A → passthrough → 2.34 A
- CSV 7.22 A → passthrough → 7.22 A

**Conflict detected** → `canonical_value = None`, conflict preserved:
```json
{
  "canonical_field": "rated_current",
  "canonical_value": null,
  "outcome": "conflict",
  "conflicts": [{
    "value_a": 2.34, "unit_a": "A",
    "source_a": {"raw_value": "2.34", "source_type": "pdf"},
    "value_b": 7.22, "unit_b": "A",
    "source_b": {"raw_value": "7.22", "source_type": "csv"}
  }]
}
```

Phase 3 will determine that the CSV column `full_load_current_a` actually contains torque data (Nm), making the PDF value authoritative for `rated_current`.
