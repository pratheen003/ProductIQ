# ProductIQ Extraction Layer Specification

**Module:** `productiq.extraction`  
**Phase:** 1 of 9  
**Status:** Frozen / Complete  

---

## 1. Overview & Separation of Concerns

The extraction layer is strictly responsible for answering: **"What does the source say?"**

```
RAW SOURCES ──► EXTRACTION (Phase 1) ──► RAW EVIDENCE ──► NORMALIZATION (Phase 2)
```

Extraction **MUST NEVER**:
- Convert units (e.g., HP to kW, lb to kg).
- Impute or guess missing values.
- Calculate values using physics formulas (e.g., computing current from power).
- Resolve contradictions between sources.
- Generate artificial data when network or file reads fail.

---

## 2. Core Data Models

Defined in `productiq/extraction/models.py`:

### `EvidenceRecord`
A single atomic fact extracted from a specific location within a source:
- `product_id`: Identifier of the associated motor (e.g. `PIQ-W22SP-4P-1.1`).
- `source_id`: Identifier of the source document/resource.
- `source_type`: `"pdf"` | `"csv"` | `"web"`.
- `attribute`: Name of the field/spec extracted (e.g. `"rated_power"`).
- `raw_value`: Exact string from source document (e.g. `"1.1"`).
- `value`: Parsed float or `None`.
- `unit`: Extracted or column unit string (e.g. `"kW"`, `"rpm"`).
- `page`: PDF 1-indexed page number (`None` for non-PDF).
- `row`: CSV 1-indexed row number (`None` for non-CSV).
- `column`: CSV column header string (`None` for non-CSV).
- `url`: Web source URL (`None` for non-web).
- `section`: Heading or section context.
- `method`: Extraction method (`"table"`, `"column"`, `"html_table"`, `"html_dl"`, `"text"`).
- `confidence`: Heuristic extraction confidence score in `[0.0, 1.0]`.
- `evidence_text`: Contextual snippet (table row, surrounding text, or sentence).

### `ExtractionResult`
Container for the extraction outcome of a single source for a specific product:
- `product_id`, `source_id`, `source_type`
- `status`: `"success"` | `"partial"` | `"failed"`
- `evidence`: List of `EvidenceRecord` objects
- `error`: Error message if status is `"failed"` or `"partial"`
- `source_ref`: Path or URL of the source
- `pages_read` / `rows_read`: Scan statistics

---

## 3. Extractor Implementations

### PDF Extractor (`PDFExtractor`)
- **File:** `productiq/extraction/pdf_extractor.py`
- **Library:** `pdfplumber`
- **Design:** The WEG brochure table uses a 20-column fixed-position data layout across pages 5, 6, and 7. The extractor reads the table rows without assuming standard single-row table headers, mapping column indices directly to spec attributes (`col[0]=kW`, `col[2]=Frame`, `col[10]=kg`, `col[12]=rpm`, `col[15]=Eff%`, `col[18]=PF`, `col[19]=Current`).
- **Poles & Global Specs:** Pole configuration is detected from page section titles (`"IV pole"` → 4, `"VI pole"` → 6). Universal specifications (`400 V`, `50 Hz`) are extracted from text headers as global evidence.

### CSV Extractor (`CSVExtractor`)
- **File:** `productiq/extraction/csv_extractor.py`
- **Library:** Python standard library `csv.DictReader`
- **Design:** Safely reads legacy CSV format, strips BOM headers, preserves row numbers and column names, and maps non-empty cells into evidence records with full-row text context. Never discards unmapped columns.

### Web Extractor (`WebExtractor`)
- **File:** `productiq/extraction/web_extractor.py`
- **Library:** `requests` + `BeautifulSoup` (lxml)
- **Design:** Implements 3 hierarchical parsing strategies (HTML `<table>`, `<dl>/<dt>/<dd>`, and regex text matching).
- **Error Handling:** Robust timeout and HTTP status handling. Network exceptions (such as HTTP 403) are recorded in the result without throwing unhandled exceptions or inventing mock data.

---

## 4. Output Storage Format

Outputs are saved in `data/processed/<product_id>/`:
```
data/processed/PIQ-W22SP-4P-1.1/
├── pdf_evidence.json
├── csv_evidence.json
└── web_evidence.json
```
And top-level summary at `data/processed/extraction_summary.json`.

---

## 5. Execution Commands

- Run batch extraction:
  ```bash
  python scripts/run_extraction.py
  ```
- Run Phase 1 verification:
  ```bash
  python scripts/verify_phase1.py
  ```
- Run extraction test suite:
  ```bash
  pytest tests/test_extraction*.py tests/test_phase1.py -v
  ```
