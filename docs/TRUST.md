# ProductIQ Trust Engine — Technical Reference

## Overview

The ProductIQ Trust Engine evaluates normalized product attributes, deterministic validation findings, and AI enrichment claims to produce an explainable trust report for downstream commerce systems.

---

## Module Structure

```
productiq/trust/
    __init__.py          — Public API exports
    base.py              — BaseTrustScorer and TrustScore interface (Phase 0 stub maintained)
    models.py            — TrustStatus, PublishabilityStatus, AttributeTrustResult, ClaimTrustResult, ReviewItem, ProductTrustReport, BatchTrustReport
    evaluator.py         — MotorTrustEvaluator deterministic rules and scoring engine
    service.py           — ProductTrustAnalyzer, BatchTrustAnalyzer orchestrators
```

---

## Data Models

### 1. `AttributeTrustResult`

| Field | Type | Description |
|---|---|---|
| `field` | str | Canonical field name (e.g. `rated_voltage`, `rated_current`) |
| `canonical_value` | Optional[Any] | Normalized value in canonical unit (or `None` if conflicted/missing) |
| `canonical_unit` | Optional[str] | Canonical unit string (e.g. `V`, `A`, `kW`) |
| `trust_status` | `TrustStatus` | `TRUSTED`, `REVIEW_REQUIRED`, `CONFLICTED`, `UNVERIFIED`, `UNSUPPORTED`, `MISSING` |
| `publishability` | `PublishabilityStatus` | `PUBLISHABLE`, `PUBLISHABLE_WITH_WARNING`, `REVIEW_REQUIRED`, `NOT_PUBLISHABLE` |
| `validation_status` | Optional[str] | `PASS`, `WARNING`, `CONFLICT`, `FAIL`, `NOT_CHECKED` |
| `is_conflicted` | bool | `True` if multi-source discrepancy detected |
| `evidence_sources` | List[str] | Provenance pointers (e.g. `["pdf:p.5", "csv:row.1"]`) |
| `confidence_score` | float | 0.0 to 1.0 deterministic score |
| `reason` | str | Human-readable explanation of the trust determination |
| `validation_rule_ids` | List[str] | Associated Phase 3 validation rules |

### 2. `ClaimTrustResult`

| Field | Type | Description |
|---|---|---|
| `claim_text` | str | The generated commercial or technical claim |
| `category` | str | `performance`, `mechanical`, `electrical`, `application`, etc. |
| `claim_type` | str | `SOURCE_BACKED`, `INFERRED`, `UNSUPPORTED` |
| `trust_status` | `TrustStatus` | Trust tier |
| `publishability` | `PublishabilityStatus` | Commercial catalog status |
| `supporting_fields` | List[str] | Technical fields supporting the claim |
| `evidence_sources` | List[str] | Original document references |
| `confidence` | float | Confidence score |
| `reason` | str | Traceable explanation |

### 3. `ReviewItem`

| Field | Type | Description |
|---|---|---|
| `review_id` | str | Unique identifier (e.g. `REV-PIQ-W22SP-4P-1.1-rated_current-conflict`) |
| `target_type` | str | `attribute`, `claim`, `validation` |
| `target_name` | str | Field or rule identifier |
| `severity` | str | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `issue_type` | str | `CONFLICT`, `WARNING`, `FAIL`, `UNVERIFIED_INFERENCE`, `MISSING_DATA` |
| `description` | str | Clear explanation of why human review is required |
| `conflicting_values` | Optional[List[dict]] | Dual-source breakdown with raw and normalized numbers |
| `validation_rule_id` | Optional[str] | Rule ID that triggered the review item |
| `recommended_action` | str | Specific recommended engineering action |

---

## Deterministic Trust Scoring Formula

$$S_{\text{overall}} = \max\left(0.0, \min\left(1.0, w_c \cdot C + w_v \cdot V + w_d \cdot D - P_{\text{conflict}}\right)\right)$$

Where:
- **$C$ (Completeness Score):** Ratio of populated canonical technical attributes ($w_c = 0.35$).
- **$V$ (Validity Score):** Validation check pass rate across attempted physical & engineering rules ($w_v = 0.35$).
- **$D$ (Source Diversity):** Score reflecting multi-source evidence presence ($w_d = 0.30$; $\ge 2$ sources = 1.0, 1 source = 0.75).
- **$P_{\text{conflict}}$ (Conflict Penalty):** $0.15 \times \text{number of conflicted attributes}$ (capped at 0.50).

Every trust report renders this formula string verbatim in `trust_score_formula`.

---

## Python API Usage

```python
from productiq.trust import ProductTrustAnalyzer, BatchTrustAnalyzer

# Evaluate a single product
analyzer = ProductTrustAnalyzer()
report = analyzer.analyze("PIQ-W22SP-4P-1.1", data_dir="data", save_output=True)

print(f"Overall status : {report.overall_trust_status.value}")
print(f"Trust score    : {report.trust_score}")
print(f"Formula        : {report.trust_score_formula}")
print(f"Review items   : {len(report.review_queue)}")

# Run batch evaluation across dataset
batch_analyzer = BatchTrustAnalyzer()
batch_report = batch_analyzer.analyze_dataset(data_dir="data", save_output=True)
print(f"Average score  : {batch_report.avg_trust_score}")
```

---

## CLI Runner

```bash
# Run batch trust evaluation across all dataset products
python scripts/run_trust.py
```
