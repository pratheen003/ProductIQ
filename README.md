# ProductIQ — AI-Powered Product Intelligence for Industrial Commerce

[![Phase 0: Foundation](https://img.shields.io/badge/Phase%200-Complete-brightgreen.svg)](#phase-status)
[![Phase 1: Extraction](https://img.shields.io/badge/Phase%201-Complete-brightgreen.svg)](#phase-status)
[![Phase 2: Normalization](https://img.shields.io/badge/Phase%202-Complete-brightgreen.svg)](#phase-status)
[![Phase 3: Validation](https://img.shields.io/badge/Phase%203-Complete-brightgreen.svg)](#phase-status)
[![Phase 4: Enrichment](https://img.shields.io/badge/Phase%204-Complete-brightgreen.svg)](#phase-status)
[![Phase 5: Trust Intelligence](https://img.shields.io/badge/Phase%205-Complete-brightgreen.svg)](#phase-status)
[![Phase 6: Frontend UI](https://img.shields.io/badge/Phase%206-Complete-brightgreen.svg)](#phase-status)
[![Tests](https://img.shields.io/badge/Tests-Phase%206%20Verified-success.svg)](#running-tests)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](#quick-start)
[![Next.js](https://img.shields.io/badge/Next.js-14%20(App%20Router)-black.svg)](#frontend-ui)

ProductIQ transforms fragmented, inconsistent industrial product data into structured, explainable, and audit-ready product intelligence.

> **Note:** For details on the parallel Unilog General Industrial Catalog pipeline workstream, see [`docs/CATALOG_PIVOT.md`](docs/CATALOG_PIVOT.md).

---

## 1. Problem

Industrial distributors, engineering procurement teams, and B2B commerce platforms manage millions of technical product specifications scattered across:
1. **Unstructured manufacturer PDF datasheets and brochures**
2. **Legacy ERP and catalog CSV exports**
3. **Manufacturer web product pages**

These data sources are rife with unit mismatches (`HP` vs `kW`), conflicting specifications (e.g. torque values labeled as current), missing parameters, and untraceable claims. Traditional pipelines either rely on manual data entry or naive LLM extraction that silently invents values, hallucinates missing parameters, and resolves discrepancies behind a black box.

---

## 2. Solution

ProductIQ provides an **evidence-first, provenance-preserving product intelligence pipeline**. Every extracted fact is an atomic observation tied to its exact origin (PDF page, CSV row/column, Web URL). Conflicts are surfaced rather than hidden, and data quality is scored with formula-visible explainability.

---

## 3. Core Ideas & Innovations

- **Immutable Provenance:** Every technical specification is wrapped in a container that tracks every document, page, and row that asserted it.
- **Strict 4-Tier Status System:** Every field is explicitly classified as `Verified`, `Inferred`, `Conflicted`, or `Unknown`.
- **Zero-Hallucination & Anti-Overwriting Principle:** The system preserves source evidence and does not silently invent or resolve conflicting values. Missing values remain `Unknown`; failed network requests record errors without inventing mock data.
- **Physics-Grounded Validation (Complete ✅):** Deterministic electromechanical engineering formulas (mechanical torque-power-speed, synchronous speed/slip, IEC 60034-30-1 efficiency) validate parameters.
- **Grounded AI Enrichment (Complete ✅):** Multi-provider LLM abstraction (Groq + OpenAI) generating commerce intelligence with strict claim separation and conflict preservation.
- **Trust-Aware Product Intelligence (Complete ✅):** Independent attribute trust, claim validation, structured review queue, and deterministic mathematical scoring ($S = 0.35 C + 0.35 V + 0.30 D - P$).

---

## 4. How ProductIQ Works

```
┌─────────────────────────────────────────────────────────────┐
│                      RAW SOURCE TIER                        │
│   • Official Manufacturer PDF Datasheets                    │
│   • Legacy Catalog / ERP CSV Exports                        │
│   • Manufacturer Web Catalog References                     │
└──────────────┬──────────────┬──────────────┬────────────────┘
               │              │              │
               ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│             PHASE 1: MULTI-SOURCE EXTRACTION                │
│   PDFExtractor          CSVExtractor       WebExtractor     │
│   (pdfplumber)          (csv.DictReader)   (bs4 + requests) │
└──────────────┬──────────────┬──────────────┬────────────────┘
               │              │              │
               └──────────────┼──────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   RAW EVIDENCE DATA MODEL                   │
│   EvidenceRecord:                                           │
│     product_id, source_id, source_type, attribute,          │
│     raw_value, value, unit, page/row/column/url,            │
│     method, confidence, evidence_text                       │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│          PERSISTENCE LAYER (data/processed/)                │
│   data/processed/<product_id>/                              │
│     ├── pdf_evidence.json                                   │
│     ├── csv_evidence.json                                   │
│     └── web_evidence.json                                   │
│   data/processed/extraction_summary.json                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│             PHASE 2: NORMALIZATION (COMPLETE ✅)            │
│   Unit conversions (HP→kW, g→kg), canonical schema mapping  │
│   Provenance-preserving, conflict-surfacing, no-LLM         │
│   data/processed/<product_id>/normalized_product.json        │
├─────────────────────────────────────────────────────────────┤
│             PHASE 3: VALIDATION (COMPLETE ✅)                │
│   409 deterministic findings across 12 products             │
│   61 conflicts surfaced, 0 silently resolved                 │
│   Engineering: Torque-Power-RPM, IE3, synchronous speed      │
│   Hard gate: 2.34 A (PDF) vs 7.22 A (CSV) detected          │
│   data/processed/<product_id>/validation_report.json        │
├─────────────────────────────────────────────────────────────┤
│             PHASE 4: GROUNDED ENRICHMENT (COMPLETE ✅)      │
│   Multi-provider LLM abstraction (Groq + OpenAI)            │
│   Commercial summaries, applications, search keywords       │
│   120+ structured claims with provenance tracking           │
│   data/processed/<product_id>/enrichment.json               │
├─────────────────────────────────────────────────────────────┤
│             PHASE 5: TRUST INTELLIGENCE (COMPLETE ✅)       │
│   Independent attribute & claim trust classification        │
│   Publishability gating (PUBLISHABLE / REVIEW_REQUIRED)     │
│   Structured review queue with action items (62 items)      │
│   Deterministic scoring: S = 0.35C + 0.35V + 0.30D - P      │
│   data/processed/<product_id>/trust_report.json             │
├─────────────────────────────────────────────────────────────┤
│             PHASE 6: PRODUCT INTELLIGENCE UI (Planned)      │
│   Human-inspectable dashboard & review queue                │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Current Prototype Status

| Stage | Component | Status | Implementation Details |
|---|---|:---:|---|
| **Phase 0** | **Foundation & Schema** | **COMPLETE** ✅ | Frozen Pydantic v2 `MotorProduct` schema, 4-tier `DataStatus`, `CANONICAL_UNITS`, config & logging |
| **Phase 1** | **Extraction Layer** | **COMPLETE** ✅ | Multi-source extractors (PDF, CSV, Web), 1,837 evidence records, automated batch pipeline |
| **Phase 2** | **Normalization** | **COMPLETE** ✅ | Deterministic unit conversion (HP→kW, W→kW, g→kg), provenance preservation, conflict surfacing, 12/12 products normalized |
| **Phase 3** | **Validation** | **COMPLETE** ✅ | Deterministic rules engine, 409 findings, 61 conflicts surfaced (never resolved), torque-power-RPM engineering check, known 2.34A vs 7.22A conflict explicitly detected |
| **Phase 4** | **AI Enrichment** | **COMPLETE** ✅ | Grounded LLM enrichment via Groq / OpenAI, structured commercial summaries, applications, keywords, conflict preservation |
| **Phase 5** | **Trust Intelligence** | **COMPLETE** ✅ | Independent attribute trust, claim validation, review queue, publishability gating, deterministic scoring ($S = 0.35C + 0.35V + 0.30D - P$) |
| **Phase 6** | **Product UI** | **NOT STARTED** ⏳ | Visual dashboard & conflict review queue |

---

## 6. Dataset

ProductIQ is tested and validated against real industrial equipment data:
- **Scope:** 12 industrial electric motors from the **WEG W22 Severe Process IE3** motor line (10× 4-pole, 2× 6-pole).
- **Sources:**
  - `data/pdf/WEG_W22_Severe_Process_IE3_Brochure.pdf` (2.5 MB official brochure)
  - `data/csv/legacy_motors.csv` (12-row legacy catalog dataset)
  - `data/web/*.url.txt` (12 official catalog web references)
- **Manifest:** `data/dataset_manifest.json` tracks source provenance across all 12 products.

---

## 7. Technology Stack

- **Language:** Python 3.10+
- **Data Validation & Typing:** Pydantic v2
- **PDF Extraction:** pdfplumber
- **HTML Parsing & Web:** BeautifulSoup4, requests, lxml
- **Testing & Quality Assurance:** pytest, pytest-cov
- **LLM Integration Layer:** OpenAI/Groq SDKs (configured with strict exception isolation)

---

## 8. Quick Start

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Installation
```bash
# Clone the repository
git clone <repo-url>
cd ProductIq

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
cp .env.example .env
# Edit .env to set GROQ_API_KEY (primary) or OPENAI_API_KEY (optional)
```

### 4. Run Pipeline Batch Runners
```bash
# Run Phase 1 Batch Extraction
python scripts/run_extraction.py

# Run Phase 2 Batch Normalization
python scripts/run_normalization.py

# Run Phase 3 Batch Validation
python scripts/run_validation.py

# Run Phase 4 Batch AI Enrichment (Groq Provider)
python scripts/run_enrichment.py

# Run Phase 5 Batch Trust Intelligence Evaluation
python scripts/run_trust.py
```

### 5. Run Verification Audits
```bash
# Verify Phase 0 Foundation
python scripts/verify_phase0.py

# Verify Phase 1 Extraction Layer
python scripts/verify_phase1.py

# Verify Phase 2 Normalization Layer
python scripts/verify_phase2.py

# Verify Phase 3 Validation Layer
python -X utf8 scripts/verify_phase3.py

# Verify Phase 4 AI Enrichment Layer
python -X utf8 scripts/verify_phase4.py

# Verify Phase 5 Trust-Aware Intelligence Layer
python -X utf8 scripts/verify_phase5.py
```

---

## 9. Running Tests

```bash
# Run the complete test suite
python -m pytest tests/ -v
```

**Current Test Results:**
- All tests passing across 12 test suites (unit, schema, extraction, normalization, validation, enrichment, trust intelligence, multi-provider abstraction, failure handling, and regression tests).

---

## 10. Project Structure

```
ProductIq/
├── data/
│   ├── csv/legacy_motors.csv            # 12-row legacy catalog dataset
│   ├── pdf/WEG_W22_Severe_Process_...   # 2.5 MB manufacturer PDF
│   ├── web/*.url.txt                    # 12 catalog web URL references
│   ├── processed/                       # Evidence, normalized, validation, enrichment, and trust JSON files
│   ├── dataset_manifest.json            # Product identity and source registry
│   └── README.md                        # Dataset provenance & copyright notice
├── docs/
│   ├── ARCHITECTURE.md                  # Complete 9-phase pipeline architecture
│   ├── DATASET.md                       # Comprehensive motor specifications
│   ├── DEVELOPMENT_LOG.md               # Truthful development chronology
│   ├── EXTRACTION.md                    # Extraction layer technical specification
│   ├── NORMALIZATION.md                 # Normalization layer technical specification
│   ├── VALIDATION.md                    # Validation layer technical specification
│   ├── ENRICHMENT.md                    # AI Enrichment technical specification
│   ├── TRUST.md                         # Trust Intelligence technical specification
│   ├── PHASE_0.md                       # Phase 0 foundation reference
│   ├── PHASE_1.md                       # Phase 1 extraction reference
│   ├── PHASE_2.md                       # Phase 2 normalization reference
│   ├── PHASE_3.md                       # Phase 3 validation reference
│   ├── PHASE_4.md                       # Phase 4 AI enrichment reference
│   ├── PHASE_5.md                       # Phase 5 trust intelligence reference
│   ├── ROADMAP.md                       # Project roadmap (Phase 0–8)
│   └── SCHEMA.md                        # Frozen canonical schema documentation
├── productiq/
│   ├── schema/                          # FROZEN: canonical MotorProduct schema
│   │   ├── __init__.py
│   │   └── motor.py
│   ├── extraction/                      # Phase 1: PDF, CSV, Web extractors
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── pdf_extractor.py
│   │   ├── csv_extractor.py
│   │   └── web_extractor.py
│   ├── normalization/                   # Phase 2: Unit conversion, parsing, normalization
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── unit_converter.py
│   │   ├── value_parser.py
│   │   ├── attribute_mapper.py
│   │   ├── base.py
│   │   └── normalizer.py
│   ├── validation/                      # Phase 3: Deterministic rules & engineering validator
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── rules.py
│   │   ├── base.py
│   │   └── validator.py
│   ├── enrichment/                      # Phase 4: Grounded AI enrichment & claims engine
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── prompts.py
│   │   ├── base.py
│   │   └── service.py
│   ├── trust/                           # Phase 5: Trust-aware intelligence & publishability engine
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── models.py
│   │   ├── evaluator.py
│   │   └── service.py
│   ├── api/                             # Phase 6: FastAPI backend service bridge
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── service.py
│   │   └── app.py
│   ├── llm/                             # Multi-provider LLM API client wrapper (Groq + OpenAI)
│   ├── config.py                        # Typed configuration loader
│   └── logging_setup.py                 # Structured logging
├── frontend/                            # Phase 6: Next.js 14 TypeScript Frontend
│   ├── app/                             # Next.js App Router pages (Dashboard, Catalog, Detail, Batch, Reviews, Ingest)
│   ├── components/                      # UI, Layout, and Recharts visualization components
│   ├── lib/                             # Typed API client, TypeScript definitions, and utility helpers
│   ├── package.json
│   └── tailwind.config.ts
├── scripts/
│   ├── run_extraction.py                # Batch extraction CLI runner
│   ├── run_normalization.py             # Batch normalization CLI runner
│   ├── run_validation.py                # Batch validation CLI runner
│   ├── run_trust.py                     # Batch trust evaluation CLI runner
│   ├── run_api.py                       # FastAPI server CLI runner (port 8000)
│   ├── verify_phase0.py                 # Phase 0 audit script (11 checks)
│   ├── verify_phase1.py                 # Phase 1 audit script (11 checks)
│   ├── verify_phase2.py                 # Phase 2 audit script (13 checks)
│   ├── verify_phase3.py                 # Phase 3 audit script (16 checks)
│   ├── verify_phase4.py                 # Phase 4 audit script (18 checks)
│   ├── verify_phase5.py                 # Phase 5 audit script (20 checks)
│   └── verify_phase6.py                 # Phase 6 audit script (20 checks)
├── tests/                               # Unit & integration tests
│   ├── test_schema.py
│   ├── test_phase0.py
│   ├── test_llm.py
│   ├── test_extraction_contract.py
│   ├── test_extraction_pdf.py
│   ├── test_extraction_csv.py
│   ├── test_extraction_web.py
│   ├── test_phase1.py
│   ├── test_phase2.py
│   ├── test_phase3.py
│   ├── test_phase4.py
│   ├── test_phase5.py
│   └── test_api.py
├── docs/                                # Technical phase documentation
│   ├── PHASE_0.md
│   ├── PHASE_1.md
│   ├── PHASE_2.md
│   ├── PHASE_3.md
│   ├── PHASE_4.md
│   ├── PHASE_5.md
│   ├── PHASE_6.md
│   ├── TRUST.md
│   ├── ROADMAP.md
│   └── DEVELOPMENT_LOG.md
├── .env.example                         # Environment template (no secrets)
├── .gitignore                           # Git ignore rules
├── README.md                            # Main project overview
├── walkthrough.md                       # Complete engineering walkthrough
└── requirements.txt                     # Project dependencies
```

---

## 11. Known Limitations

1. **WEG.net Anti-Bot Blocking:** Live HTTP requests to `weg.net` catalog URLs are blocked with HTTP 403 Forbidden. ProductIQ captures this failure state verbatim without hallucinating data.
2. **Preserved Raw Data Anomaly:** `data/csv/legacy_motors.csv` lists `full_load_current_a = 7.22` for the 1.1 kW motor, which is the torque value from the PDF brochure table. This is intentionally surfaced as a conflict by Phase 2/3, preserved with warnings by Phase 4, and placed in the Phase 5/6 human Review Queue with `REVIEW_REQUIRED` publishability status without picking an arbitrary winner.

---

## 12. Roadmap & Next Steps

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for full phase-by-phase objectives.  
**Immediate Next Step:** **Phase 7 — Advanced Human-in-the-Loop Audit Trails & Syndication** [NOT STARTED].
