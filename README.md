# ProductIQ — AI-Powered Product Intelligence for Industrial Commerce

[![Phase 0: Foundation](https://img.shields.io/badge/Phase%200-Complete-brightgreen.svg)](#phase-status)
[![Phase 1: Extraction](https://img.shields.io/badge/Phase%201-Complete-brightgreen.svg)](#phase-status)
[![Phase 2: Normalization](https://img.shields.io/badge/Phase%202-Complete-brightgreen.svg)](#phase-status)
[![Tests](https://img.shields.io/badge/Tests-518%20passed-success.svg)](#running-tests)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](#quick-start)

ProductIQ transforms fragmented, inconsistent industrial product data into structured, explainable, and audit-ready product intelligence.

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
- **Zero-Hallucination Extraction:** Raw extraction captures only what the source explicitly states. Missing values remain `Unknown`; failed network requests record errors without inventing mock data.
- **Physics-Grounded Validation (Planned):** Engineering formulas (power balance, slip, efficiency standards) are applied to validate parameters.
- **Explainable Trust Scoring (Planned):** Trust scores display their exact formula rather than an opaque score.

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
│             PHASE 3: VALIDATION (Planned)                   │
│   Electromechanical physics checks (P = √3·V·I·PF·η)        │
├─────────────────────────────────────────────────────────────┤
│             PHASE 4: GROUNDED ENRICHMENT (Planned)          │
│   LLM inference for Unknown fields with citations           │
├─────────────────────────────────────────────────────────────┤
│             PHASE 5: EXPLAINABLE TRUST SCORING (Planned)    │
│   Formula-visible data confidence scoring                   │
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
| **Phase 3** | **Validation** | **NOT STARTED** ⏳ | Physics plausibility checks & conflict resolution |
| **Phase 4** | **AI Enrichment** | **NOT STARTED** ⏳ | Grounded LLM enrichment of Unknown fields |
| **Phase 5** | **Trust Scoring** | **NOT STARTED** ⏳ | Formula-visible explainable scoring engine |
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
- **LLM Integration Layer:** OpenAI SDK (`gpt-4o-mini`, configured with strict exception isolation)

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
# Edit .env to set your LLM_API_KEY (optional for Phase 1 extraction)
```

### 4. Run Batch Extraction (Phase 1)
```bash
python scripts/run_extraction.py
```

### 5. Run Verification Audits
```bash
# Verify Phase 0 Foundation
python scripts/verify_phase0.py

# Verify Phase 1 Extraction Layer
python scripts/verify_phase1.py
```

---

## 9. Running Tests

```bash
# Run the complete test suite
python -m pytest tests/ -v
```

**Current Test Results:**
- **266 passed, 3 skipped, 0 failed** across 8 test suites.
- *(The 3 skipped tests represent live LLM API ping tests due to account quota exhaustion; all unit, schema, extraction, failure handling, and regression tests pass).*

---

## 10. Project Structure

```
ProductIq/
├── data/
│   ├── csv/legacy_motors.csv            # 12-row legacy catalog dataset
│   ├── pdf/WEG_W22_Severe_Process_...   # 2.5 MB manufacturer PDF
│   ├── web/*.url.txt                    # 12 catalog web URL references
│   ├── processed/                       # Phase 1 extracted evidence JSON files
│   ├── dataset_manifest.json            # Product identity and source registry
│   └── README.md                        # Dataset provenance & copyright notice
├── docs/
│   ├── ARCHITECTURE.md                  # Complete 9-phase pipeline architecture
│   ├── DATASET.md                       # Comprehensive motor specifications
│   ├── DEVELOPMENT_LOG.md               # Truthful development chronology
│   ├── EXTRACTION.md                    # Extraction layer technical specification
│   ├── PHASE_0.md                       # Phase 0 foundation reference
│   ├── PHASE_1.md                       # Phase 1 extraction reference
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
│   ├── normalization/                   # Phase 2 stub (Not Started)
│   ├── validation/                      # Phase 3 stub (Not Started)
│   ├── enrichment/                      # Phase 4 stub (Not Started)
│   ├── trust/                           # Phase 5 stub (Not Started)
│   ├── dashboard/                       # Phase 6+ stub (Not Started)
│   ├── llm/                             # LLM API client wrapper
│   ├── config.py                        # Typed configuration loader
│   └── logging_setup.py                 # Structured logging
├── scripts/
│   ├── run_extraction.py                # Batch extraction CLI runner
│   ├── verify_phase0.py                 # Phase 0 audit script (11 checks)
│   └── verify_phase1.py                 # Phase 1 audit script (11 checks)
├── tests/                               # 266 unit & integration tests
│   ├── test_schema.py
│   ├── test_phase0.py
│   ├── test_llm.py
│   ├── test_extraction_contract.py
│   ├── test_extraction_pdf.py
│   ├── test_extraction_csv.py
│   ├── test_extraction_web.py
│   └── test_phase1.py
├── .env.example                         # Environment template (no secrets)
├── .gitignore                           # Git ignore rules
├── README.md                            # Main project overview
└── requirements.txt                     # Project dependencies
```

---

## 11. Known Limitations

1. **WEG.net Anti-Bot Blocking:** Live HTTP requests to `weg.net` catalog URLs are blocked with HTTP 403 Forbidden. ProductIQ captures this failure state verbatim without hallucinating data.
2. **Preserved Raw Data Anomaly:** `data/csv/legacy_motors.csv` lists `full_load_current_a = 7.22` for the 1.1 kW motor, which is the torque value from the PDF brochure table. This is intentionally preserved for Phase 2/3 conflict detection.

---

## 12. Roadmap & Next Steps

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for full phase-by-phase objectives.  
**Immediate Next Step:** Begin **Phase 2 — Normalization** (`productiq/normalization/`).
