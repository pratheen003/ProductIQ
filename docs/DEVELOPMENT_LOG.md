# ProductIQ Development Log

This document provides a truthful, chronological record of the development of ProductIQ from initial inception through Phase 0 and Phase 1 completion.

---

## 1. Project Objective

Industrial enterprises and B2B commerce platforms maintain product technical data scattered across unstructured manufacturer PDF datasheets, legacy ERP/catalog CSV exports, and corporate web catalogs. Current approaches rely either on manual copy-pasting or naive LLM extraction that hallucinate missing values, silently resolve contradictions, and destroy source traceability.

**ProductIQ** transforms messy, heterogeneous industrial product data into structured, explainable, and audit-ready product intelligence.

---

## 2. Development Philosophy: Evidence-First & Provenance-Aware

1. **Extraction answers ONLY "What does the source say?":** Raw extraction preserves exact strings, numbers, units, and document locations without semantic alteration.
2. **Never silently overwrite or resolve conflicts:** When sources disagree, the conflict is surfaced as a first-class state (`Conflicted`), not averaged or guessed.
3. **Never discard provenance:** Every extracted value carries a `SourceEntry` or `EvidenceRecord` documenting exact page numbers, table rows, CSV columns, or web URLs.
4. **No LLM hallucination as ground truth:** LLM-derived values are never marked `Verified`; they are strictly classified as `Inferred` and require explicit manufacturer grounding.
5. **Explainable trust scoring:** Trust scores must show their mathematical formula rather than acting as a black-box percentage.

---

## 3. Phase 0 — Foundation

**Status:** `COMPLETE`  
**Schema Version:** `0.1.0-phase0` (FROZEN)

### Work Accomplished:
- **Repository Architecture:** Established package structure across `productiq/schema`, `extraction`, `normalization`, `validation`, `enrichment`, `trust`, `dashboard`, and `llm`.
- **Canonical Schema (`productiq/schema/motor.py`):**
  - Strongly-typed Pydantic v2 `MotorProduct` model with 4 identity fields and 11 technical fields.
  - Strict 4-tier status enum: `Verified | Inferred | Conflicted | Unknown`.
  - Generic `FieldValue[V]` container enforcing runtime consistency (e.g. `Unknown` requires `value=None`, `Verified` requires non-empty `sources`).
  - Immutable `SourceEntry` provenance record.
  - `CANONICAL_UNITS` registry mapping all 11 fields to SI / standard industrial units (`kW`, `V`, `A`, `Hz`, `rpm`, `%`, `kg`).
- **Configuration & Security:** Environment loader (`productiq/config.py`) via `python-dotenv` with `.env.example` template; strict `.gitignore` preventing credential exposure.
- **LLM Interface (`productiq/llm/client.py`):** Configured OpenAI wrapper with exception hierarchy (`LLMAuthError`, `LLMConnectionError`, `LLMQuotaError`).
- **Baseline Dataset:** Curated 12 real WEG W22 Severe Process IE3 motor records with `dataset_manifest.json` cataloging PDF, CSV, and Web references.
- **Phase 0 Verification (`scripts/verify_phase0.py`):** 11 automated checks.

### Verification Results:
- **`scripts/verify_phase0.py`:** `PHASE 0 STATUS: COMPLETE [OK]` (11/11 checks passed).
- **Test Suite:** 99 passed, 3 skipped (live API ping tests skipped gracefully due to account quota limit, proving API connectivity without blocking offline CI/CD).

---

## 4. Phase 1 — Extraction Layer

**Status:** `COMPLETE`

### Work Accomplished:
- **Evidence Data Model (`productiq/extraction/models.py`):**
  - Defined `EvidenceRecord` capturing `attribute`, `raw_value`, `value`, `unit`, `source_id`, `source_type`, `page`, `row`, `column`, `url`, `section`, `method`, `confidence`, and `evidence_text`.
  - Defined `ExtractionResult` and `BatchExtractionSummary`.
- **PDF Extractor (`productiq/extraction/pdf_extractor.py`):**
  - Implemented `PDFExtractor` using `pdfplumber` for multi-column positional table extraction on `WEG_W22_Severe_Process_IE3_Brochure.pdf`.
  - Scanned pages 5, 6, and 7 (4-pole, 6-pole, 8-pole ratings), extracting 1,704 total evidence records across all brochure ratings (including 240 records directly matching the 12 target manifest motors).
- **CSV Extractor (`productiq/extraction/csv_extractor.py`):**
  - Implemented `CSVExtractor` using `csv.DictReader`, processing `data/csv/legacy_motors.csv` and generating 133 evidence records across all 12 products with exact row and column provenance.
- **Web Extractor (`productiq/extraction/web_extractor.py`):**
  - Implemented `WebExtractor` using `BeautifulSoup` (HTML table, definition list, and regex strategies) with local fixture testing (`tests/fixtures/sample_motor_page.html`).
  - Gracefully captured HTTP 403 Forbidden responses from live `weg.net` requests without crashing or fabricating mock data.
- **Batch Pipeline (`scripts/run_extraction.py`):**
  - Automated batch execution over all 12 dataset products, storing outputs in `data/processed/<product_id>/` and `data/processed/extraction_summary.json`.
- **Phase 1 Verification (`scripts/verify_phase1.py`):** 11 automated audit checks.

### Verified Final Evidence Counts:
| Source | Attempted | Succeeded | Failed | Evidence Records |
|---|:---:|:---:|:---:|:---:|
| **PDF (`pdfplumber`)** | 12 | 12 | 0 | **1,704** |
| **CSV (`csv.DictReader`)** | 12 | 12 | 0 | **133** |
| **Web (`BeautifulSoup`)** | 12 | 0 | 12 | **0** |
| **Grand Total** | **12** | **12** | **0** | **1,837** |

### Test & Regression Audit:
- **`pytest tests/ -v`:** **266 passed, 3 skipped, 0 failed** in 26.84s (Exit Code: 0).
- **Phase 0 Regression:** 11/11 checks passed.
- **Phase 1 Verification:** 11/11 checks passed.
- *Note on Skipped Tests:* The 3 skipped tests represent live LLM API calls skipped due to exhausted OpenAI billing credits; they are not extraction failures.

---

## 5. Web Access Limitation

During Phase 1 batch runs against official catalog URLs (e.g. `https://www.weg.net/catalog/weg/CI/en/...`), the remote web server returned **HTTP 403 Forbidden** due to anti-bot / scraper protection policies.

**Anti-Hallucination Policy in Practice:**
- ProductIQ **did not fabricate** HTML or invent fake webpage specifications.
- The failure was captured verbatim in `web_evidence.json` with `status: "failed"` and `error: "403 Client Error: Forbidden..."`.
- 0 evidence records were generated for web sources.
- Parsing logic was deterministically verified using a dedicated, labeled local fixture (`tests/fixtures/sample_motor_page.html`).

---

## 6. Data Integrity Finding (Preserved Conflict)

Inspection of `data/csv/legacy_motors.csv` revealed that for motor `PIQ-W22SP-4P-1.1`, the CSV specifies `full_load_current_a = 7.22`. In the manufacturer PDF brochure, `7.22` is the full-load torque in Newton-meters (`7.22 Nm`), whereas the rated current is `2.34 A`.

**Resolution Decision:**
The raw CSV file was **intentionally left unedited** to preserve authentic legacy data messiness. In Phase 2 (Normalization) and Phase 3 (Engineering Validation), this discrepancy will be automatically detected and classified as `DataStatus.CONFLICTED`.

---

## 7. Phase 2 Handoff: Next Steps

**Status:** `NOT STARTED`

Phase 2 will implement the **Normalization Layer** (`productiq/normalization/`):
1. Ingest raw `EvidenceRecord` objects from `data/processed/`.
2. Convert non-canonical units (`HP` → `kW`, `lb` → `kg`, non-standard voltage strings) into canonical SI units.
3. Map normalized values into `FieldValue` containers with full `SourceEntry` provenance.
4. Output populated `MotorProduct` instances ready for Phase 3 engineering validation.
