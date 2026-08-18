# ProductIQ — Engineering Walkthrough

## The Pipeline in One Sentence

Raw manufacturer documents → structured, normalized, explainable motor product intelligence — with every transformation traceable to its source.

---

## Phase Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RAW SOURCES                               │
│  WEG W22 Brochure PDF  │  Legacy CSV  │  WEG web (403)     │
└────────────┬────────────┴──────┬───────┴────────────────────┘
             │ Phase 1 Extraction│
             ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   EVIDENCE LAYER                            │
│  1,704 PDF evidence records  │  133 CSV records  │  0 web  │
│  data/processed/<product_id>/pdf_evidence.json etc.         │
└────────────────────────┬────────────────────────────────────┘
                         │ Phase 2 Normalization
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              NORMALIZED PRODUCT LAYER                        │
│  12 × normalized_product.json                               │
│  Canonical units  │  Full provenance  │  Conflict flags     │
└────────────────────────┬────────────────────────────────────┘
                         │ Phase 3 (future)
                         ▼
                   VALIDATION + TRUST SCORING
                         │ Phase 4 (future)
                         ▼
                 ENRICHMENT + DASHBOARD
```

---

## Phase 0 — Foundation (Complete)

Established the frozen canonical schema that every downstream phase builds on:

- **`MotorProduct`**: 11 technical fields, each wrapped in `FieldValue` (value + unit + status + sources)
- **`DataStatus` enum**: Verified / Inferred / Conflicted / Unknown — four tiers, non-negotiable
- **`CANONICAL_UNITS`**: Single source of truth for unit strings (`rated_power → kW`, `weight → kg`, etc.)
- **`SourceEntry`**: Provenance model — source ID, type, location, reference

**Verification:** `python scripts/verify_phase0.py` → 11/11 checks ✅

---

## Phase 1 — Extraction (Complete)

Implemented PDF, CSV, and web extractors that produce `EvidenceRecord` objects:

```python
@dataclass
class EvidenceRecord:
    source_id:   str          # e.g. "WEG_W22_Severe_Process_IE3_Brochure"
    source_type: str          # "pdf" | "csv" | "web"
    product_id:  str
    attribute:   str          # e.g. "rated_power", "full_load_current_a"
    raw_value:   str          # EXACTLY as it appeared in the source
    value:       float        # parsed numeric (if applicable)
    unit:        Optional[str]
    page:        Optional[int]  # PDF page number
    row:         Optional[int]  # CSV row number
    column:      Optional[str]  # CSV column name
    confidence:  float
```

**Results:**
- PDF: 1,704 evidence records across 12 products
- CSV: 133 evidence records
- Web: 0 records (WEG.net returns HTTP 403 — correctly recorded as failure, not fabricated)
- Total: 1,837 evidence records

**Verification:** `python scripts/verify_phase1.py` → 11/11 checks ✅

---

## Phase 2 — Normalization (Complete)

### What Phase 2 Does

Transforms raw evidence → canonical product data while preserving every provenance link.

### Concrete example: 1100 W → 1.1 kW

**Input** (evidence record from a hypothetical CSV):
```
attribute:  "rated_power"
raw_value:  "1100"
unit:       "W"
source:     csv, row 5, column "rated_power_w"
confidence: 0.85
```

**Step 1: Attribute mapping**
```python
get_mapping("rated_power") → ("rated_power", CANONICAL, "Power in W → convert to kW")
```

**Step 2: Value parsing**
```python
parse_numeric("1100") → (1100.0, None)   # unit comes from EvidenceRecord.unit = "W"
```

**Step 3: Unit conversion**
```python
convert_value("rated_power", 1100.0, "W") → (1.1, "kW")
# Exact factor: 1 W = 0.001 kW  →  1100.0 × 0.001 = 1.1 kW
```

**Step 4: EvidenceRef construction (provenance preserved)**
```python
EvidenceRef(
    raw_value   = "1100",     # exact source string — never changed
    raw_unit    = "W",        # unit as found in source
    parsed_value = 1100.0,
    source_type = "csv",
    row         = 5,
    column      = "rated_power_w",
    confidence  = 0.85,
)
```

**Output** (NormalizedField):
```json
{
  "canonical_field": "rated_power",
  "canonical_value": 1.1,
  "canonical_unit": "kW",
  "outcome": "normalized",
  "evidence_refs": [{
    "raw_value": "1100",
    "raw_unit": "W",
    "parsed_value": 1100.0,
    "source_type": "csv",
    "column": "rated_power_w"
  }]
}
```

**Audit trail:** From the normalized output, any reviewer can trace `1.1 kW` → `"1100"` W → CSV row 5 → original source document.

---

### Concrete example: Conflict preserved without resolution

**Inputs:**

| Source | attribute | raw_value | unit | Normalizes to |
|---|---|---|---|---|
| PDF (page 5, table) | `rated_current` | `"2.34"` | A | 2.34 A |
| CSV (column `full_load_current_a`) | `rated_current` | `"7.22"` | A | 7.22 A |

**Conflict detection:**
```python
is_equivalent("rated_current", 2.34, "A", 7.22, "A")
# → False  (|2.34 - 7.22| = 4.88, far exceeds 1e-6 tolerance)
```

**Phase 2 action: preserve both, pick no winner**
```json
{
  "canonical_field": "rated_current",
  "canonical_value": null,
  "outcome": "conflict",
  "conflicts": [{
    "value_a": 2.34, "unit_a": "A",
    "source_a": {"raw_value": "2.34", "source_type": "pdf", "page": 5},
    "value_b": 7.22, "unit_b": "A",
    "source_b": {"raw_value": "7.22", "source_type": "csv", "column": "full_load_current_a"}
  }]
}
```

**Why Phase 2 doesn't resolve this:** The CSV column `full_load_current_a` is actually mislabeled — it contains torque data (Nm) from the brochure table, not current. This mislabeling is detected by cross-field consistency analysis (P = √3 × V × I × PF × η), which is Phase 3's job. Phase 2's job is to surface the discrepancy faithfully.

---

## Engineering Discipline

### Status system rigorously enforced

| Phase 2 action | Status assigned |
|---|---|
| Successful unit conversion | Remains `passthrough` / `normalized` (NOT `Verified`) |
| Two sources agree on value | `passthrough` (NOT `Verified` — that requires cross-validation) |
| Two sources disagree | `conflict` |
| No evidence | `missing` |

Normalization succeeding ≠ verification. That distinction is critical for trustworthy product intelligence.

### Nothing silently disappears

- **Unmapped attributes** (torque, inertia, partial-load data): preserved in `unmapped_evidence`
- **Parse failures**: captured as `NormalizationIssue`, not swallowed
- **Unknown units**: captured as `NormalizationIssue`, not guessed
- **HTTP 403 web failures**: recorded as `status: "failed"`, produce zero evidence

### Determinism guaranteed

The same evidence input always produces byte-for-byte identical normalized output. No randomness, no timestamps in canonical values, no LLM calls.

---

## Verification

```bash
python scripts/verify_phase0.py   # 11/11 ✅
python scripts/verify_phase1.py   # 11/11 ✅
python scripts/verify_phase2.py   # 13/13 ✅
python -m pytest tests/ -v        # 518 passed, 3 skipped ✅
```

---

## What's Next (Phase 3 — Validation)

Phase 3 will receive from Phase 2:
1. **12 × `normalized_product.json`** — canonical fields with `outcome` flags
2. **49 conflict records** — each with both evidence sources preserved
3. **144 unmapped evidence refs** — torque, inertia, partial-load data for future field expansion

Phase 3 will use cross-field physics equations to resolve conflicts and assign final `DataStatus` (Verified / Inferred / Conflicted / Unknown) to each field.
