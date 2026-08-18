# ProductIQ Motor Schema Reference

**Schema Version:** `0.1.0-phase0`  
**Status:** FROZEN — do not modify without a version bump and team review  
**Module:** `productiq/schema/motor.py`  
**Import:** `from productiq.schema import DataStatus, FieldValue, MotorProduct, SourceEntry, CANONICAL_UNITS`

---

## 1. Data Status Enum

Every technical field in a `MotorProduct` carries a `DataStatus`. This is a strict enum — no strings, no integers, no alternatives.

| Value | Meaning | When to use |
|---|---|---|
| `Verified` | Confirmed from a reliable source (typically manufacturer PDF or catalog) | Only after extraction from a real source; requires `sources` to be non-empty |
| `Inferred` | Derived by calculation, assumption, or LLM reasoning | Must cite the inference source; never used for raw extraction |
| `Conflicted` | Two or more sources disagree | Surface the conflict; never silently pick a winner |
| `Unknown` | No value available | Default state; `value` must be `None`; never convert to a guess |

**Non-negotiable constraints enforced by Pydantic:**
- `status=Unknown` → `value` must be `None`
- `status=Verified` or `status=Inferred` → `sources` must be non-empty
- Any other status string → `ValidationError` at instantiation

---

## 2. Source Entry

Every observation must record exactly where it came from.

```python
class SourceEntry:
    source_id:   str         # Unique document identifier
    source_type: SourceType  # "pdf" | "web" | "csv"
    location:    str         # Human-readable location in the document
    reference:   str         # URL or file path to the source
```

**Example:**
```json
{
  "source_id": "weg-w22sp-brochure-2023",
  "source_type": "pdf",
  "location": "p.5, IV pole table, row 1.1 kW",
  "reference": "https://static.weg.net/medias/downloadcenter/hf9/hd0/WEG-w22-severe-process-european-market-50058022-brochure-english-web.pdf"
}
```

A field can hold **multiple SourceEntry records**. This is required for conflict detection — if two sources give different values, both entries are preserved and the field status is set to `Conflicted`.

---

## 3. Field Value

Every technical specification is wrapped in a `FieldValue` container — never stored as a bare Python primitive.

```python
class FieldValue[V]:
    value:      Optional[V]         # The extracted or computed value
    unit:       Optional[str]       # Canonical unit string (see table below)
    status:     DataStatus          # Verified | Inferred | Conflicted | Unknown
    confidence: Optional[float]     # 0.0–1.0; None when Unknown
    sources:    List[SourceEntry]   # All observations for this field
```

**Minimum JSON representation for an Unknown field:**
```json
{
  "value": null,
  "unit": "kW",
  "status": "Unknown",
  "confidence": null,
  "sources": []
}
```

**Minimum JSON representation for a Verified field:**
```json
{
  "value": 1.1,
  "unit": "kW",
  "status": "Verified",
  "confidence": 0.98,
  "sources": [
    {
      "source_id": "weg-w22sp-brochure-2023",
      "source_type": "pdf",
      "location": "p.5, IV pole table, row 1.1 kW",
      "reference": "https://static.weg.net/..."
    }
  ]
}
```

---

## 4. Canonical Unit Registry

All downstream modules must use these units. **Never invent alternative unit strings.**

| Field | Canonical Unit | Type | Notes |
|---|---|---|---|
| `rated_power` | `kW` | float | Shaft output power |
| `rated_voltage` | `V` | float | Supply voltage |
| `rated_current` | `A` | float | Full-load current |
| `frequency` | `Hz` | float | Supply frequency |
| `rated_speed` | `rpm` | float | Full-load speed |
| `poles` | *(none — dimensionless)* | int | Number of magnetic poles |
| `efficiency` | `%` | float | 0–100; full-load efficiency |
| `power_factor` | *(none — dimensionless)* | float | 0.00–1.00 |
| `weight` | `kg` | float | Motor weight |
| `ip_rating` | *(none — string descriptor)* | str | e.g. "IP55", "IP56" |
| `frame_size` | *(none — string descriptor)* | str | e.g. "132M", "L90S" |

---

## 5. Motor Product (Top-Level Record)

```python
class MotorProduct:
    # Identity (plain strings — stable identifiers, not extracted measurements)
    product_id:   str   # e.g. "PIQ-W22SP-4P-1.1"
    manufacturer: str   # e.g. "WEG"
    model:        str   # e.g. "W22 Severe Process IE3 (4-pole)"
    product_type: str   # default: "three_phase_induction_motor"

    # Technical specification fields (all FieldValue with canonical units)
    rated_power:   FieldValue  # kW
    rated_voltage: FieldValue  # V
    rated_current: FieldValue  # A
    frequency:     FieldValue  # Hz
    rated_speed:   FieldValue  # rpm
    poles:         FieldValue  # dimensionless
    efficiency:    FieldValue  # %
    power_factor:  FieldValue  # dimensionless
    weight:        FieldValue  # kg
    ip_rating:     FieldValue  # string
    frame_size:    FieldValue  # string

    schema_version: str  # "0.1.0-phase0"
```

---

## 6. Schema Rules (must never be violated)

1. **All downstream modules import from `productiq.schema` only.** Never redefine the product structure.
2. **Never store a bare value** — always wrap in `FieldValue`.
3. **Never overwrite a source entry** — append new observations, preserve all.
4. **Conflict → status=Conflicted** — never silently pick one value over another.
5. **LLM output → status=Inferred** — never Verified.
6. **Unknown → value=None** — enforced by Pydantic validator.
7. **Verified/Inferred → sources non-empty** — enforced by Pydantic validator.

---

## 7. Serialization

```python
# Serialize
json_str = motor.to_json(indent=2)

# Deserialize
motor = MotorProduct.from_json(json_str)
```

The schema serializes cleanly to/from JSON via Pydantic's `model_dump_json()` / `model_validate()`.
