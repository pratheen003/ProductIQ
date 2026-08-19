# Phase 5 — Trust-Aware Product Intelligence

## 1. Objective

Transform normalized data (Phase 2), deterministic validation findings (Phase 3), and AI enrichment claims (Phase 4) into an explainable, audit-ready, commerce-safe trust intelligence layer for industrial equipment.

**Traditional AI Commerce System:**
```
RAW DATA → LLM → PRODUCT DESCRIPTION (Black box, hallucinations unflagged, conflicts hidden)
```

**ProductIQ Trust-Aware Architecture:**
```
SCATTERED DATA → EVIDENCE EXTRACTION (Phase 1)
               → CANONICAL NORMALIZATION (Phase 2)
               → DETERMINISTIC VALIDATION & CONFLICT DETECTION (Phase 3)
               → GROUNDED AI ENRICHMENT (Phase 4)
               → TRUST INTELLIGENCE ENGINE (Phase 5)
               → EXPLAINABLE COMMERCE INTELLIGENCE (Audit trail, Review Queue, Publishability)
```

Phase 5 answers the core commercial questions:
- Which specifications are **100% verified** and safe to publish immediately?
- Which specifications have **multi-source conflicts** and must be gated from public catalogs?
- Which AI claims are **source-backed** vs. **grounded inferences**?
- What exact action must a catalog engineer take to resolve discrepancies?

---

## 2. Core Architectural Guarantees

1. **Independent Attribute Trust:**
   Attribute-level trust is derived strictly from Phase 1 evidence, Phase 2 normalization, and Phase 3 validation rules — **never** blindly inferred from Phase 4 LLM confidence numbers.
2. **Validation-Aware Claim Trust:**
   Phase 4 AI enrichment claims are classified using their structured metadata (`is_source_backed`, `confidence`, `evidence_sources`) and cross-checked against underlying attribute validation status. If a claim references a conflicted attribute (such as `rated_current`), the claim itself is flagged `CONFLICTED` and gated with `REVIEW_REQUIRED`.
3. **No Silent Conflict Resolution:**
   ProductIQ never picks arbitrary winners. Disagreements between manufacturer datasheets and legacy CSV records remain surfaced with full dual-source provenance.
4. **Deterministic & Cost-Free Execution:**
   Trust evaluation runs as a fast, 100% deterministic rules engine requiring zero additional LLM tokens or API calls.
5. **Formula-Visible Trust Scoring:**
   Every product trust score is mathematically calculated and displays its rendered formula:
   $$S_{\text{overall}} = \text{clamp}(0.35 \cdot S_{\text{completeness}} + 0.35 \cdot S_{\text{validity}} + 0.30 \cdot S_{\text{diversity}} - P_{\text{conflict}}, 0.0, 1.0)$$

---

## 3. Trust Classification & Publishability Tiers

### Trust Statuses (`TrustStatus`)

| Status | Meaning | Action / Handling |
|---|---|---|
| `TRUSTED` | Verified from manufacturer source evidence and passed all validation checks | Fully trusted ground truth |
| `REVIEW_REQUIRED` | Flagged with a validation warning or uncertainty | Requires catalog engineer confirmation |
| `CONFLICTED` | Multiple sources report conflicting values (e.g. PDF vs CSV) | Gated from publication; review item generated |
| `UNVERIFIED` | AI-grounded inference (e.g. frequency `50 Hz`) | Usable for search discovery with disclaimer |
| `UNSUPPORTED` | Failed electromechanical engineering check or physical bound | Blocked; data correction required |
| `MISSING` | Parameter is absent across all provided sources | Omitted from published catalog |

### Publishability Statuses (`PublishabilityStatus`)

| Status | Commerce Catalog Meaning |
|---|---|
| `PUBLISHABLE` | Safe for customer-facing commercial catalogs as verified specification |
| `PUBLISHABLE_WITH_WARNING` | Safe to publish with informational / inferred badge |
| `REVIEW_REQUIRED` | Blocked from automatic publication; queued for human review |
| `NOT_PUBLISHABLE` | Missing or untrusted; excluded from public view |

---

## 4. Real Data Analysis & Examples

### Example A: The Known Conflict Hard Gate (`PIQ-W22SP-4P-1.1` — `rated_current`)

- **Field:** `rated_current`
- **Canonical Value:** `null` (zero winner picked)
- **Trust Status:** `CONFLICTED`
- **Publishability:** `REVIEW_REQUIRED`
- **Confidence Score:** `0.30`
- **Reason:** `"CONFLICT: Source disagreement: pdf reports 2.34 A vs csv reports 7.22 A. No single winner picked — resolution requires human review."`
- **Evidence Provenance:** `["pdf:p.5 (rated_current)", "csv:row.1 (rated_current)"]`
- **Review Queue Item:**
  - `review_id`: `"REV-PIQ-W22SP-4P-1.1-rated_current-conflict"`
  - `severity`: `"HIGH"`
  - `issue_type`: `"CONFLICT"`
  - `recommended_action`: `"Inspect physical nameplate or official dimension drawing to resolve 'rated_current'."`

### Example B: The Clean Publishable Path (`PIQ-W22SP-4P-1.1` — `rated_voltage`)

- **Field:** `rated_voltage`
- **Canonical Value:** `400.0 V`
- **Trust Status:** `TRUSTED`
- **Publishability:** `PUBLISHABLE`
- **Confidence Score:** `1.0`
- **Reason:** `"Verified from manufacturer source evidence and passed all validation checks."`
- **Evidence Provenance:** `["pdf:p.4", "pdf:p.5", "pdf:p.6", "pdf:p.7"]`
- **Catalog Handling:** Immediate commercial publication with verified badge.

---

## 5. Dataset Metrics (12 WEG W22 Motors)

```
============================================================
  Trust Evaluation Summary
============================================================
  Total products evaluated     : 12
  Trusted products             : 0 (all have preserved CSV legacy conflicts)
  Conflicted products          : 12
  Review required products     : 0
  Average trust score          : 0.4133
  Total review items generated : 62
```

Every product in the dataset is thoroughly analyzed, with all legacy CSV discrepancies (e.g. torque values mislabeled as current) cleanly isolated in the review queue while uncontested specifications (voltage, power, frame size, weight) are marked `PUBLISHABLE`.

---

## 6. Phase 6 Boundary

**Phase 6 (Product Intelligence UI / Dashboard) is NOT STARTED.**
Phase 5 produces machine-readable JSON artifacts (`data/processed/<product_id>/trust_report.json` and `data/processed/batch_trust_report.json`) that provide the complete backing data for future UI visualization.
