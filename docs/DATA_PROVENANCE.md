# ProductIQ — Complete Data Provenance & Lineage Guide
## Dataset Categorization, Lineage Tracking & Immutable Audit Trails

---

## 1. Data Classification Taxonomy

ProductIQ strictly separates all data in the repository into five distinct tiers to guarantee auditability:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DATA CLASSIFICATION TIERS                        │
├───────────────────┬──────────────────────────────────────────────────────┤
│ 1. INPUT DATA     │ Raw, unmodified source files provided as input       │
│ 2. REFERENCE DATA │ Verified dictionaries, lookup tables, standards      │
│ 3. GROUND TRUTH   │ Verified benchmark outputs used for exact validation │
│ 4. DERIVED DATA   │ Normalized models, validation findings, AI claims   │
│ 5. EXPORT OUTPUT  │ Formatted commerce-ready delivery workbooks (.xlsx)   │
└───────────────────┴──────────────────────────────────────────────────────┘
```

---

## 2. File-by-File Data Registry

### Tier 1: Input Data
| File Path | Description | Record Count | Origin / Role |
|---|---|:---:|---|
| `data/catalog/input/Unihack__Sample_Dataset_-_Input.csv` | Raw catalog sample dataset | 1,000 rows | Raw distributor catalog feed with 6 columns |
| `data/raw/catalog/weg_w22_catalog.csv` | Industrial motor catalog export | 12 motors | Legacy ERP/catalog CSV export |
| `data/raw/datasheets/weg_w22_brochure.pdf` | Official WEG W22 technical brochure | 32 pages | Manufacturer PDF technical specification |
| `data/raw/web/` | Manufacturer web catalog HTML/markdown | 12 files | Web reference specifications |

### Tier 2: Reference & Lookup Data
| File Path | Description | Entry Count | Origin / Role |
|---|---|:---:|---|
| `data/catalog/lookups/manufacturers_brands.json` | Master manufacturer/brand dictionary | 2 canonical pairs | Derived exclusively from ground-truth records |
| `data/catalog/lookups/uom_standards.json` | UOM standards & alias dictionary | 4 canonical units | Derived exclusively from ground-truth records |
| `data/catalog/lookups/decimal_fractions.json` | Fractional to decimal dimension mapping | 63 fractions | Comprehensive fractional inch conversions |

### Tier 3: Ground Truth Benchmark Data
| File Path | Description | Record Count | Origin / Role |
|---|---|:---:|---|
| `data/catalog/ground_truth/Unihack__Expected_Output_-_Delivery_Format.csv` | Expected delivery format benchmark | 2 gold rows | Source of 252 delivery headers and gold benchmark |

### Tier 4: Processed & Derived Artifacts
| File Path | Description | Output Count | Generating Engine |
|---|---|:---:|---|
| `data/processed/<product_id>/normalized_product.json` | SI-normalized motor models | 12 products | `MotorNormalizer` (Phase 2) |
| `data/processed/<product_id>/validation_report.json` | Physics validation findings | 12 reports | `MotorValidator` (Phase 3) |
| `data/processed/<product_id>/enrichment.json` | Structured commerce intelligence | 12 products | `EnrichmentService` (Phase 4) |
| `data/processed/<product_id>/trust_report.json` | Mathematical trust scoring | 12 reports | `TrustEvaluator` (Phase 5) |
| `data/catalog/processed/row_0001.json` .. `row_1000.json` | Enriched catalog JSON records | 1,000 items | `CatalogPipeline` (Prompts 1–3) |
| `data/catalog/processed/batch_catalog_report.json` | Consolidated catalog metrics | 1 batch | `run_catalog_batch.py` |

### Tier 5: Export Delivery Outputs
| File Path | Description | Column Count | Generating Engine |
|---|---|:---:|---|
| `data/catalog/processed/productiq_delivery_output.xlsx` | 252-column Excel delivery output | 252 headers | `DeliveryFormatExporter` (Prompt 3 Final) |
| `data/catalog/processed/productiq_delivery_output.csv` | 252-column CSV delivery output | 252 headers | `DeliveryFormatExporter` (Prompt 3 Final) |

---

## 3. Atomic Provenance Model (`EvidenceRecord`)

Every extracted technical parameter is encapsulated in a container preserving its full origin:

```python
class EvidenceRecord(BaseModel):
    evidence_id: str             # Unique deterministic hash
    source_type: SourceType      # PDF, CSV, WEB, LOOKUP, GROUND_TRUTH
    source_uri: str              # File path or URL
    page_number: Optional[int]   # Exact PDF page
    table_index: Optional[int]   # Table location
    row_index: Optional[int]     # CSV row number
    column_name: Optional[str]   # Source column name
    raw_text: str                # Unmodified original string
    raw_unit: Optional[str]      # Unmodified original unit
    extracted_at: datetime       # ISO timestamp
    extraction_method: str       # REGEX, TABLE_PARSER, LOOKUP_MATCH
```

When data undergoes unit conversion, the original `raw_text` and `raw_unit` remain accessible inside `EvidenceRef`, ensuring no information loss.
