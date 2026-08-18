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
- **Status:** `NOT STARTED` ⏳
- **Objective:** Convert heterogeneous extracted units (e.g. `HP` to `kW`, `lb` to `kg`, non-standard frequency strings) into SI canonical units defined in `CANONICAL_UNITS` while maintaining original raw values in `SourceEntry`.
- **Expected Output:** `UnitNormalizer`, normalized `MotorProduct` instances populated with `FieldValue` structures.

---

### Phase 3 — Engineering Validation & Physics Checks
- **Status:** `NOT STARTED` ⏳
- **Objective:** Apply fundamental electromechanical physics rules to detect errors and contradictions:
  - Power balance equation: $P = \sqrt{3} \times V \times I \times \text{PF} \times \eta$
  - Synchronous speed / slip validation: $n_s = \frac{120 \times f}{p}$; verify $n_{\text{rated}} < n_s$.
  - IEC 60034-30-1 efficiency tier verification.
- **Expected Output:** `PhysicsValidator`, automated setting of `DataStatus.CONFLICTED` with exact mathematical justifications.

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
