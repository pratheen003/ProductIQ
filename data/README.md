# ProductIQ Data Pack

This directory contains the multi-source dataset for ProductIQ across Phase 0 and Phase 1.

---

## 1. Dataset Overview

The dataset covers **12 industrial electric motors** from the **WEG W22 Severe Process IE3** motor line:
- **10 models:** 4-pole configurations (0.75 kW to 15 kW)
- **2 models:** 6-pole configurations (0.75 kW and 1.1 kW)

All product identifiers, metadata, and cross-source references are cataloged in [`dataset_manifest.json`](dataset_manifest.json).

---

## 2. Source Provenance & Descriptions

### A. Manufacturer PDF Datasheet (`data/pdf/`)
- **File:** `WEG_W22_Severe_Process_IE3_Brochure.pdf` (2.5 MB)
- **Origin:** Official WEG European market brochure (Doc: 50058022).
- **Nature:** **Real manufacturer source.** Contains multi-column technical electrical and mechanical specification tables for 2-, 4-, 6-, and 8-pole motors at 400 V / 50 Hz.
- **Copyright / Ownership:** ProductIQ makes no claim of ownership over manufacturer technical material. All trademarks and brochure contents belong to WEG S.A.

### B. Legacy Catalog CSV (`data/csv/`)
- **File:** `legacy_motors.csv` (12 rows)
- **Origin:** A legacy-style catalog file **derived directly from the real WEG brochure tables** to simulate heterogeneous legacy ERP/catalog exports.
- **Important Provenance Note:** This file is explicitly labeled as brochure-derived, not an original manufacturer-issued CSV export.
- **Preserved Anomaly:** Contains a known pre-existing discrepancy (`full_load_current_a = 7.22` on 1.1 kW motor, corresponding to the 7.22 Nm torque column). In strict accordance with ProductIQ's anti-hallucination principles, the raw file is preserved unedited so downstream normalization (Phase 2) and validation (Phase 3) can detect and flag it.

### C. Manufacturer Web References (`data/web/`)
- **Files:** `PIQ-W22SP-*.url.txt` (12 reference files)
- **Origin:** Official WEG catalog-family URLs pointing to the low-voltage IEC W22 product series on `weg.net`.
- **Status:** Automated direct HTTP requests to these URLs receive HTTP 403 Forbidden due to WEG anti-bot mechanisms. The extraction layer documents this failure state without fabricating artificial HTML content.

### D. Processed Extraction Evidence (`data/processed/`)
- **Structure:** `data/processed/<product_id>/` contains raw JSON evidence records:
  - `pdf_evidence.json`
  - `csv_evidence.json`
  - `web_evidence.json`
- **Summary:** `extraction_summary.json` provides overall batch extraction metrics.

---

## 3. Anti-Hallucination & Provenance Rules

1. **No Synthetic Data Falsely Labeled as Real:** Every record in `dataset_manifest.json` is marked with its true origin (`real_source_collected` or `derived`).
2. **Preserve Raw Observations:** Raw values and units are never silently overwritten during extraction.
3. **No Unwarranted Extrapolation:** If a field is missing from a source, it remains `Unknown` in Phase 0/1 rather than being mathematically inferred or guessed.
