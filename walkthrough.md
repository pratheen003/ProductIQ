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
│              NORMALIZED PRODUCT LAYER                        │
│  12 × normalized_product.json                               │
│  Canonical units  │  Full provenance  │  Conflict flags     │
└────────────────────────┤─────────────────────────────────────────┘
                         | Phase 3 Validation
                         v
┌─────────────────────────────────────────────────────────────┐
│              VALIDATION LAYER (COMPLETE)                     │
│  12 x validation_report.json                                │
│  409 findings  |  61 conflicts  |  Engineering checks       │
└─────────────────────────┬───────────────────────────────────┘
                          | Phase 4 AI Enrichment (Groq)
                          v
┌─────────────────────────────────────────────────────────────┐
│              AI ENRICHMENT LAYER (COMPLETE)                  │
│  12 x enrichment.json  |  Multi-provider LLM                │
│  120+ structured claims |  Anti-hallucination verified      │
└─────────────────────────┬───────────────────────────────────┘
                          | Phase 5 Trust Intelligence
                          v
┌─────────────────────────────────────────────────────────────┐
│              TRUST INTELLIGENCE LAYER (COMPLETE)             │
│  12 x trust_report.json |  Review Queue (62 items)          │
│  Deterministic scoring  |  Commerce Publishability Gating   │
└─────────────────────────┬───────────────────────────────────┘
                          | Phase 6 (future)
                          v
                 DASHBOARD & REVIEW UI
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
python scripts/verify_phase0.py   # 11/11
python scripts/verify_phase1.py   # 11/11
python scripts/verify_phase2.py   # 13/13
python -X utf8 scripts/verify_phase3.py  # 16/16
python -m pytest tests/ -v        # 634 passed (116 new in Phase 3)
```

---

## Phase 3 — Validation Engine (Complete)

Phase 3 implemented a deterministic, offline-capable validation engine:

### Architecture

```
NormalizedProduct
      v
 MotorValidator (productiq/validation/validator.py)
      v
 [Category A] Schema       — canonical units, version
 [Category B] Required     — rated_power, rated_voltage, rated_speed
 [Category D] Range        — positive values, physical bounds
 [Category F] Consistency  — cross-source conflicts
 [Category G] Engineering  — Torque-Power-RPM, IE3 efficiency, synchronous speed
 [Category H] Missing      — optional field inventory
 [Category I] Known conflicts — PDF 2.34 A vs CSV 7.22 A
      v
ProductValidationReport (409 findings per batch)
```

### Key outcomes

| Metric | Value |
|---|---|
| Products validated | 12 / 12 |
| Total findings | 409 |
| PASS findings | 311 (76%) |
| CONFLICT findings | 61 |
| WARNING findings | 2 |
| Conflicts silently resolved | **0** |
| Engineering checks | Torque (PASS), Synchronous speed (PASS), IE3 efficiency |

### Hard gate: known conflict

Rule `CONFLICT_RATED_CURRENT_PDF_VS_CSV` fires for `PIQ-W22SP-4P-1.1`:

```
PDF rated_current = 2.34 A  (source: WEG W22 brochure, page 5, table row)
CSV rated_current = 7.22 A  (source: legacy_motors.csv, col full_load_current_a)
Note: 7.22 matches full_load_torque_nm (Nm) — possible mislabeling
Action: CONFLICT finding, canonical_value = null — no winner picked
```

### Engineering plausibility

For `PIQ-W22SP-4P-1.1` (1.1 kW, 1455 rpm, reported T = 7.22 Nm):
```
T_expected = (1.1 x 1000 x 60) / (2 x pi x 1455) = 7.219 Nm
Difference = 0.0%  ->  PASS (tolerance: 15%)
```

## Phase 4 — AI Enrichment Layer (Complete)

Phase 4 implemented a grounded, multi-provider AI enrichment engine using Groq (`openai/gpt-oss-20b`):

### Architecture

```
NormalizedProduct + ProductValidationReport
                     v
  MotorEnricher (productiq/enrichment/service.py)
                     v
  [Context Builder]  — separates verified facts, unmapped torque/speed, and conflict records
  [System Prompt v4] — strict anti-hallucination & conflict preservation rules
  [Groq LLM Client] — structured JSON generation with rate-limit retry backoff
  [Post-Processor]  — forces unresolved conflicts to be preserved, tags claim provenance
                     v
ProductEnrichment (12 x enrichment.json)
```

### Phase 4 Outcomes

| Metric | Value |
|---|---|
| Products enriched | 12 / 12 (100%) |
| LLM Provider | Groq (`openai/gpt-oss-20b`) |
| Prompt version | `4.0.0` |
| Total structured claims | 120+ claims |
| Source-backed claims | Fully grounded in Phase 1/Phase 2 evidence |
| Inferred claims | Explicitly tagged with confidence and reasoning notes |
| Conflicts silently resolved | **0** (100% preserved) |

---

## Phase 5 — Trust-Aware Product Intelligence (Complete)

Phase 5 introduces deterministic, explainable trust evaluation, review queue generation, and commercial publishability gating:

### Architecture

```
NormalizedProduct (Phase 2) + ValidationReport (Phase 3) + ProductEnrichment (Phase 4)
                                    v
                 MotorTrustEvaluator (productiq/trust/evaluator.py)
                                    v
   [Attribute Trust Engine]  — independently checks Phase 1 evidence & Phase 3 rules
   [Claim Trust Engine]      — classifies AI claims & checks underlying attribute status
   [Review Queue Builder]    — generates structured action items with WHAT/WHY/ACTION
   [Deterministic Scorer]    — calculates S = clamp(0.35C + 0.35V + 0.30D - P, 0.0, 1.0)
   [Publishability Engine]   — gates attributes into PUBLISHABLE vs REVIEW_REQUIRED
                                    v
                 ProductTrustReport (12 x trust_report.json)
```

### Key Highlights & Real Data Verification

1. **Known Conflict Hard Gate (`PIQ-W22SP-4P-1.1` — `rated_current`):**
   - Discrepancy between PDF brochure (2.34 A) and legacy CSV (7.22 A) is assigned `TrustStatus.CONFLICTED` and `PublishabilityStatus.REVIEW_REQUIRED`.
   - Zero winner picked (`canonical_value = null`).
   - Generates action item `REV-PIQ-W22SP-4P-1.1-rated_current-conflict` with explicit recommended action.
2. **Clean Publishable Parameter (`PIQ-W22SP-4P-1.1` — `rated_voltage`):**
   - Clean 400.0 V with manufacturer datasheet evidence and PASS validation is assigned `TrustStatus.TRUSTED` and `PublishabilityStatus.PUBLISHABLE`.
3. **Deterministic Math:**
   - Evaluates all 12 products in milliseconds with zero LLM API costs.
   - Outputs full mathematical formula string for visual auditability.

---

## Verification & Audit Checklist

```bash
# Verify Phase 0 Foundation
python scripts/verify_phase0.py       # 11/11 PASSED

# Verify Phase 1 Extraction
python scripts/verify_phase1.py       # 11/11 PASSED

# Verify Phase 2 Normalization
python scripts/verify_phase2.py       # 13/13 PASSED

# Verify Phase 3 Validation
python -X utf8 scripts/verify_phase3.py  # 16/16 PASSED

# Verify Phase 4 AI Enrichment
python -X utf8 scripts/verify_phase4.py  # 18/18 PASSED

# Verify Phase 5 Trust Intelligence
python -X utf8 scripts/verify_phase5.py  # 20/20 PASSED

# Run full pytest regression suite
python -m pytest tests/ -v            # 679/679 PASSED
```

---

## What's Next: Phase 6 (Product Intelligence UI / Dashboard)

**Status:** `NOT STARTED`

Phase 6 will consume the JSON artifacts created across Phases 1–5 to render an interactive web dashboard:
- Visual specification cards with color-coded badges (`Verified`, `Inferred`, `Conflicted`, `Unknown`)
- Interactive review queue for catalog engineers to resolve conflicts with justification
- Dual-source provenance inspector with side-by-side evidence diffs.


