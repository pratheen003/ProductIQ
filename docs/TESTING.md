# ProductIQ — Complete Testing & Verification Guide
## Comprehensive Quality Assurance & Regression Test Suite

---

## 1. Executive Test Summary

Every phase, module, pipeline layer, and mathematical model in ProductIQ is guarded by automated test suites and deterministic verification scripts.

| Test Category | Test Count | Status | Execution Command |
|---|:---:|:---:|---|
| **Phase 0–6 Verification Checks** | **109 Checks** | **109 / 109 PASSED** ✅ | `python scripts/verify_phase[0-6].py` |
| **Pytest Full Unit & Integration Suite** | **732 Tests** | **732 / 732 PASSED** ✅ | `python -m pytest -q` |
| **Next.js Production App Routes** | **12 Routes** | **12 / 12 BUILT CLEANLY** ✅ | `cd frontend && npm run build` |
| **Exact-Header Delivery Export** | **252 / 252 Headers** | **100% BYTE MATCH** ✅ | `python scripts/export_delivery_format.py` |
| **Security Secrets Audit** | **0 Secrets Tracked** | **VERIFIED CLEAN** ✅ | `git grep -i "sk-proj-"` |

---

## 2. Test Suite Breakdown by Layer

### A. Industrial Electric Motor Pipeline (`productiq/`): 688 Tests
- `tests/test_phase0_schema.py`: Schema validation, immutable field value containers, status enums (`Verified`, `Inferred`, `Conflicted`, `Unknown`), SI canonical units.
- `tests/test_extraction_*.py`: Multi-source PDF datasheet extraction (layout/table parsing), CSV catalog extraction, and Web page parsing with atomic `EvidenceRecord` preservation.
- `tests/test_normalization_*.py`: Deterministic unit conversions (HP $\to$ kW, lb $\to$ kg, V, Hz, RPM), non-standard string handling, and attribute mapping without overwriting raw evidence.
- `tests/test_phase3.py`: Engineering rule evaluation, torque-power-speed physics ($T = \frac{P \times 1000 \times 60}{2\pi \times N}$), slip/synchronous speed limits, and specific conflict detection (PDF 2.34 A vs CSV 7.22 A).
- `tests/test_phase4.py`: LLM provider abstraction (Groq + OpenAI), anti-hallucination prompt contract, structured JSON schema enforcement, and claim provenance segregation.
- `tests/test_phase5.py`: Mathematical trust scoring ($S = 0.35 C + 0.35 V + 0.30 D - P$), publishability categorization (`PUBLISHABLE`, `REVIEW_REQUIRED`), and structured review queue generation.
- `tests/test_phase6.py`: FastAPI endpoints, Pydantic DTO models, human review resolution workflow, and error handling.

### B. Unilog Catalog Intelligence Pipeline (`productiq_catalog/`): 44 Tests
- `tests/test_catalog_foundation.py` (17 tests): Catalog input loader (1,000 items), ground truth parser, 63-entry decimal-fraction table, and ground-truth-derived lookup loaders.
- `tests/test_catalog_enrichment_eval.py` (12 tests): Manufacturer canonicalization, trademark handling (`®`), UOM standards conversion, 39.2% cross-column brand conflict detection, Mechanism A exact match on gold rows, and Mechanism B vocabulary compliance metrics.
- `tests/test_catalog_prompt3.py` (9 tests): Corrected Mechanism A framing & disclaimer verification, 1,000-row batch disk persistence (`data/catalog/processed/`), catalog product explorer API, and automated deck numbers export.
- `tests/test_catalog_delivery_export.py` (6 tests): Exact 252-header delivery format schema match, byte-for-byte column ordering, openpyxl `.xlsx` and `.csv` generation, empty cell compliance for unpopulated columns, and API download attachment headers.

---

## 3. How to Run the Test Suites

### Run Full Pytest Regression Suite:
```bash
python -m pytest -v
```

### Run Phase-by-Phase Verification Scripts:
```bash
python scripts/verify_phase0.py
python scripts/verify_phase1.py
python scripts/verify_phase2.py
python -X utf8 scripts/verify_phase3.py
python -X utf8 scripts/verify_phase4.py
python scripts/verify_phase5.py
python scripts/verify_phase6.py
```

### Run Catalog Evaluation & Export Runners:
```bash
python scripts/run_catalog_eval.py
python scripts/run_catalog_batch.py
python scripts/export_delivery_format.py
python scripts/export_deck_numbers.py
```

### Build & Validate Next.js Frontend:
```bash
cd frontend
npm run build
```

---

## 4. Invariant Tests Enforced

1. **No-Fabrication Invariant:** Tests assert that when an input value is outside verified lookup tables, `status` resolves strictly to `DataStatus.UNKNOWN` with `confidence = 0.0`. Never guessed.
2. **Conflict Preservation Invariant:** Tests assert that when multi-source evidence disagrees, both evidence references are preserved, `status` resolves to `DataStatus.CONFLICTED`, and no silent winner is chosen.
3. **Exact Header Invariant:** Tests assert that the exported delivery format file contains all 252 columns in exact sequence matching `Unihack__Expected_Output_-_Delivery_Format.csv`.
