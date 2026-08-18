# ProductIQ Phase 0 — Foundation

**Status:** COMPLETE  
**Date:** 2026-08-18  
**Phase:** 0 of 9  

---

## Objective

Establish the frozen foundation that all subsequent phases build on:
- A canonical, strongly-typed motor schema
- A strict four-tier data status enum
- Real source material for an initial motor dataset
- A working LLM API connection
- Clean module boundaries for the full pipeline
- Automated verification that everything actually works

---

## Completed Tasks

| # | Task | Status |
|---|---|---|
| 1 | Motor attribute schema finalized (Pydantic v2) | ✅ |
| 2 | DataStatus enum frozen (Verified/Inferred/Conflicted/Unknown) | ✅ |
| 3 | Canonical units defined for all 11 technical fields | ✅ |
| 4 | Multi-source provenance structure implemented (FieldValue.sources) | ✅ |
| 5 | Schema Pydantic validators enforce constraints at runtime | ✅ |
| 6 | Repository/module structure created with clean boundaries | ✅ |
| 7 | Configuration system (python-dotenv, typed Config dataclass) | ✅ |
| 8 | .env.example exists; no real keys committed | ✅ |
| 9 | README with setup instructions | ✅ |
| 10 | 12 real WEG W22 Severe Process IE3 motors collected | ✅ |
| 11 | Dataset manifest with source provenance for all 12 products | ✅ |
| 12 | LLM API client with env-based key, timeout, error handling | ✅ |
| 13 | LLM API connectivity verified (ping test) | ✅ |
| 14 | Phase 0 verification command (`scripts/verify_phase0.py`) | ✅ |
| 15 | Documentation: SCHEMA.md, PHASE_0.md, DATASET.md, ARCHITECTURE.md | ✅ |
| 16 | Automated test suite: test_schema.py, test_phase0.py, test_llm.py | ✅ |

---

## Schema Summary

**File:** `productiq/schema/motor.py`  
**Version:** `0.1.0-phase0`

- **DataStatus enum:** `Verified | Inferred | Conflicted | Unknown`  
- **FieldValue:** generic container with `value`, `unit`, `status`, `confidence`, `sources`  
- **SourceEntry:** provenance record with `source_id`, `source_type`, `location`, `reference`  
- **MotorProduct:** 4 identity fields + 11 technical FieldValue fields  
- **CANONICAL_UNITS:** registry mapping all 11 field names to their canonical unit strings  

All constraints enforced by Pydantic validators:
- `Unknown` status → `value` must be `None`
- `Verified`/`Inferred` → `sources` must be non-empty
- Any invalid status string → `ValidationError`

---

## Dataset Summary

**Source:** WEG W22 Severe Process IE3 motors, official manufacturer brochure  
**Brochure:** `data/pdf/WEG_W22_Severe_Process_IE3_Brochure.pdf` (real PDF, 2.5 MB)  
**Origin URL:** https://static.weg.net/medias/downloadcenter/hf9/hd0/WEG-w22-severe-process-european-market-50058022-brochure-english-web.pdf

| Motor | Poles | Rated Power |
|---|---|---|
| PIQ-W22SP-4P-1.1 | 4 | 1.1 kW |
| PIQ-W22SP-4P-1.5 | 4 | 1.5 kW |
| PIQ-W22SP-4P-2.2 | 4 | 2.2 kW |
| PIQ-W22SP-4P-3.0 | 4 | 3.0 kW |
| PIQ-W22SP-4P-4.0 | 4 | 4.0 kW |
| PIQ-W22SP-4P-5.5 | 4 | 5.5 kW |
| PIQ-W22SP-4P-7.5 | 4 | 7.5 kW |
| PIQ-W22SP-4P-9.2 | 4 | 9.2 kW |
| PIQ-W22SP-4P-11 | 4 | 11.0 kW |
| PIQ-W22SP-4P-15 | 4 | 15.0 kW |
| PIQ-W22SP-6P-0.75 | 6 | 0.75 kW |
| PIQ-W22SP-6P-1.1 | 6 | 1.1 kW |

**Source types per product:** PDF (real) + CSV (derived from brochure, properly labeled) + Web URL reference  
**Provenance status:** All 12 marked `real_source_collected`  
**Synthetic data:** None. All data derived from or referencing the real WEG manufacturer brochure.

---

## Repository Architecture

```
productiq/
├── schema/          FROZEN — single source of truth for all types
├── extraction/      Phase 1 stub — BaseExtractor interface defined
├── normalization/   Phase 2 stub — BaseNormalizer interface defined
├── validation/      Phase 3 stub — BaseValidator interface defined
├── enrichment/      Phase 4 stub — BaseEnricher interface defined
├── trust/           Phase 5 stub — BaseTrustScorer + TrustScore defined
├── dashboard/       Phase 6+ stub
├── llm/             LLMClient — connectivity proven, enrichment not implemented
├── config.py        Environment loader
└── logging_setup.py Structured logging

data/
├── pdf/             WEG_W22_Severe_Process_IE3_Brochure.pdf (real, 2.5 MB)
├── csv/             legacy_motors.csv (12 rows, brochure-derived)
├── web/             12 × .url.txt references
├── processed/       Empty — populated by Phase 1
└── dataset_manifest.json

tests/
├── test_schema.py   30+ unit tests for schema types and constraints
├── test_phase0.py   Integration tests for all Phase 0 exit criteria
└── test_llm.py      LLM config and live connectivity tests

scripts/
└── verify_phase0.py Phase 0 verification command

docs/
├── SCHEMA.md        Complete schema reference (this is it)
├── PHASE_0.md       Phase 0 documentation (this file)
├── DATASET.md       Dataset provenance and collection notes
└── ARCHITECTURE.md  Full Phase 0–9 pipeline diagram
```

---

## LLM Setup

**Provider:** OpenAI  
**Client:** `productiq/llm/client.py` → `LLMClient`  
**Key source:** `LLM_API_KEY` environment variable only (never hard-coded)  
**Default model:** `gpt-4o-mini` (override with `LLM_MODEL` env var)  
**Phase 0 test:** `client.ping()` — sends trivial JSON prompt, validates response  

---

## Known Limitations

1. **Dataset is single-manufacturer, single-series.** All 12 motors are WEG W22 Severe Process IE3. Phase 1 should add motors from at least one additional manufacturer (e.g., ABB, Siemens, or SEW-Eurodrive) to exercise cross-manufacturer conflict detection.

2. **IP rating not in CSV.** The brochure's tabular data does not list IP rating per row. `ip_rating` will remain `Unknown` for all 12 motors until Phase 1 extracts it from the brochure's text sections.

3. **Voltage not in CSV.** The brochure specifies 400 V for the IE3 table but it's a column header, not a per-row field. Phase 1 must handle this as a table-wide constant, not a missing value.

4. **No cross-manufacturer data yet.** Conflict detection (the `Conflicted` status path) cannot be exercised until Phase 1 collects data from multiple manufacturers for the same motor class.

5. **Web references are catalog-family URLs, not per-product URLs.** Phase 1 should resolve exact product URLs from the WEG catalog during web extraction.

---

## Phase 0 Exit Criteria — All Met

```
[x] Product schema finalized
[x] Status enum finalized (Verified/Inferred/Conflicted/Unknown)
[x] Canonical units documented for every field
[x] Provenance structure implemented (multi-source per field)
[x] Schema validation tests pass
[x] Repository/module structure exists
[x] Configuration system exists
[x] .env.example exists, no secrets committed
[x] README setup instructions exist
[x] Real motor source dataset collected (12 motors)
[x] Dataset manifest exists with clear source provenance
[x] LLM API client exists with proper key/env handling
[x] LLM API test succeeds with configured credentials
[x] Phase 0 verification command exists and passes
[x] Phase 0 documentation exists (SCHEMA.md, PHASE_0.md, DATASET.md, ARCHITECTURE.md)
[x] No synthetic data is falsely represented as real
[x] No future-phase core mechanics unnecessarily implemented
```

---

## Recommended First Task for Phase 1

**Task:** Implement `PDFExtractor` in `productiq/extraction/pdf_extractor.py`

**Exact starting point:**
1. Use `pdfplumber` (add to requirements.txt) to parse `data/pdf/WEG_W22_Severe_Process_IE3_Brochure.pdf`
2. Locate the 4-pole and 6-pole performance tables (pages 5–6)
3. For each row, extract: rated_power, rated_current, rated_speed, efficiency, power_factor, weight, frame_size
4. Wrap each extracted value in a `FieldValue` with `status=Verified`, `confidence=0.95`, and a `SourceEntry` citing the PDF, page, and row
5. Produce one `MotorProduct` per row, with identity fields set from the manifest
6. Write the output to `data/processed/<product_id>.json`

**Key constraints to remember:**
- Each FieldValue must have at least one SourceEntry
- Do not invent values for fields not present in the table (leave them Unknown)
- Do not mark anything Verified that comes from the CSV (that is derived data, use Inferred)
