# ProductIQ Pipeline Roadmap

**Overall Pipeline:**
```
RAW SOURCES ──► EXTRACTION (P1) ──► NORMALIZATION (P2) ──► VALIDATION (P3) ──► ENRICHMENT (P4)
            ──► TRUST SCORING (P5) ──► UI DASHBOARD (P6) ──► REVIEW QUEUE (P7) ──► BATCH AI (P8)
```

---

## Roadmap Phases

### Phase 0 — Foundation & Canonical Schema
- **Status:** `COMPLETE` ✅
- **Objective:** Establish the strongly-typed canonical data model, provenance primitives, status tiering, dataset manifest, and configuration infrastructure.
- **Outputs:** `productiq/schema/motor.py`, `MotorProduct`, `DataStatus`, `FieldValue`, `SourceEntry`, `CANONICAL_UNITS`, `scripts/verify_phase0.py`.

---

### Phase 1 — Multi-Source Extraction Layer
- **Status:** `COMPLETE` ✅
- **Objective:** Extract raw observations from PDFs, CSV catalogs, and Web pages into atomic `EvidenceRecord` objects while preserving exact locations and context without semantic distortion.
- **Outputs:** `PDFExtractor`, `CSVExtractor`, `WebExtractor`, `EvidenceRecord`, `data/processed/<product_id>/*.json`, `scripts/run_extraction.py`, `scripts/verify_phase1.py`.

---

### Phase 2 — Unit Normalization & Mapping
- **Status:** `COMPLETE` ✅
- **Objective:** Convert heterogeneous extracted units (e.g. `HP` to `kW`, `lb` to `kg`, non-standard frequency strings) into SI canonical units defined in `CANONICAL_UNITS` while maintaining original raw values in `EvidenceRef`.
- **Outputs:** `MotorNormalizer`, `BatchNormalizer`, `unit_converter.py`, `value_parser.py`, `attribute_mapper.py`, `models.py`, `scripts/run_normalization.py`, `scripts/verify_phase2.py`, `data/processed/<product_id>/normalized_product.json`.

---

### Phase 3 — Engineering Validation & Rules Engine
- **Status:** `COMPLETE` ✅
- **Objective:** Apply deterministic, explainable electromechanical engineering rules and cross-source consistency checks:
  - Canonical unit conformance (`SCHEMA_CANONICAL_UNITS`) and schema version guarding.
  - Required and important field completeness checks (`REQUIRED_FIELD_PRESENCE`, `IMPORTANT_FIELD_PRESENCE`).
  - Strict range and physical plausibility validation (positive power, voltage, speed, current, weight; efficiency ∈ [0, 100]%, PF ∈ [0, 1]).
  - Cross-source conflict surfacing with dual-evidence provenance preserved.
  - Engineering checks: Torque-Power-Speed mechanical relationship ($T = \frac{P \times 1000 \times 60}{2\pi \times N}$), synchronous speed / slip ($n_{\text{rated}} < n_s$), and IE3 class efficiency plausibility.
  - Specific conflict detection: PDF 2.34 A vs CSV 7.22 A (`CONFLICT_RATED_CURRENT_PDF_VS_CSV`), identifying likely torque/current mislabeling without picking a winner.
- **Outputs:** `productiq/validation/models.py`, `productiq/validation/rules.py`, `productiq/validation/validator.py`, `data/processed/<product_id>/validation_report.json`, `data/processed/batch_validation_report.json`, `scripts/run_validation.py`, `scripts/verify_phase3.py`.

---

### Phase 4 — Grounded LLM Enrichment
- **Status:** `NOT STARTED` ⏳
- **Objective:** Utilize LLM reasoning to enrich genuinely `Unknown` fields only, strictly requiring citations to manufacturer documentation and marking outputs as `Inferred` (never `Verified`).
- **Expected Output:** `GroundedEnricher`, enriched `MotorProduct` records with LLM prompt/version provenance.

---

### Phase 5 — Explainable Trust Scoring
- **Status:** `NOT STARTED` ⏳
- **Objective:** Compute transparent, formula-visible quality scores based on completeness, source diversity, physics validation pass rates, and conflict penalties.
- **Expected Output:** `TrustScorer`, `TrustScore` dataclass with component breakdown and rendered mathematical formula.

---

### Phase 6 — Product Intelligence UI / Dashboard
- **Status:** `NOT STARTED` ⏳
- **Objective:** Provide a web-based, human-inspectable dashboard displaying motor specifications, color-coded status badges (`Verified`/`Inferred`/`Conflicted`/`Unknown`), provenance inspector, and side-by-side conflict comparisons.
- **Expected Output:** Interactive UI dashboard.

---

### Phase 7 — Human-in-the-Loop Review Queue
- **Status:** `NOT STARTED` ⏳
- **Objective:** Enable domain engineers to review `Conflicted` fields, select canonical values with justification, and promote resolved fields to `Verified`.
- **Expected Output:** Review queue workflow and audit trail.

---

### Phase 8 — Batch Intelligence & Analytics
- **Status:** `NOT STARTED` ⏳
- **Objective:** Catalog-wide analytics, efficiency trend benchmarking across power classes, cross-manufacturer comparisons, and data completeness heatmaps.
- **Expected Output:** Batch analytics engine and export utilities.
