# ProductIQ System Architecture

**Scope:** Full Phase 0 → Phase 9 pipeline design  
**Implementation status:** Phase 0 complete ✅. Phase 1 complete ✅. Phases 2–9 are architectural targets (not yet implemented).

---

## Full Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAW SOURCE MATERIAL                         │
│  Manufacturer PDFs │ Manufacturer Websites │ Legacy CSV Catalogs │
└───────────┬─────────────────┬──────────────────────┬────────────┘
            │                 │                      │
            ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 1: EXTRACTION                            │
│  PDFExtractor │ WebExtractor │ CSVExtractor                     │
│                                                                 │
│  • Each extractor produces (field_name, FieldValue) tuples      │
│  • Every FieldValue includes a populated SourceEntry            │
│  • Raw values preserved; no normalization yet                   │
│  • Output: List[Tuple[str, FieldValue]] per motor               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 2: NORMALIZATION                         │
│  UnitNormalizer: HP→kW, V variants, rpm standardization, etc.  │
│                                                                 │
│  • Convert raw extracted units to canonical units               │
│  • Preserve original value+unit in SourceEntry before convert  │
│  • Never silently discard original values                       │
│  • Output: MotorProduct with canonically-unitized FieldValues   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 3: VALIDATION                            │
│  Engineering plausibility checks using real physics             │
│                                                                 │
│  • P = √3 × V × I × PF × η  (power balance)                   │
│  • ns = 120f/p; verify rated_speed < ns (slip check)           │
│  • IE3 efficiency bounds per IEC 60034-30-1                     │
│  • Implausible values → status=Conflicted with formula cite     │
│  • Never silently modify values; always record why              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 4: ENRICHMENT                            │
│  LLM-grounded enrichment of genuinely Unknown fields only       │
│                                                                 │
│  • Only touches fields with status=Unknown                      │
│  • LLM must cite manufacturer documentation (grounded)          │
│  • Output always status=Inferred — NEVER Verified               │
│  • SourceEntry records: model, prompt version, timestamp        │
│  • No enrichment of Verified or Inferred fields                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 5: TRUST SCORING                         │
│  Explainable, formula-visible scoring per product               │
│                                                                 │
│  Components:                                                    │
│  • Completeness score: known_fields / total_fields              │
│  • Source diversity: PDF + Web + CSV coverage                   │
│  • Conflict penalty: -N% per Conflicted field                   │
│  • Validation pass rate: physics checks passed / attempted      │
│  • Enrichment discount: Inferred < Verified                     │
│                                                                 │
│  Output: TrustScore { overall, formula, component_scores }      │
│  Formula displayed in UI — never a black-box number             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 6: PRODUCT INTELLIGENCE UI               │
│  Human-inspectable dashboard                                    │
│                                                                 │
│  • Per-field status breakdown (color-coded by DataStatus)       │
│  • Trust score with formula visible                             │
│  • Source provenance viewer (click value → see source)          │
│  • Side-by-side source comparison for Conflicted fields         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 7: REVIEW QUEUE                          │
│  Human-in-the-loop conflict resolution                          │
│                                                                 │
│  • Queue of all Conflicted fields across all products           │
│  • Reviewer selects canonical value with justification          │
│  • Resolution recorded as SourceEntry (type="human_review")     │
│  • Resolved field → status=Verified                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 8: BATCH INTELLIGENCE                    │
│  Aggregate insights across the full motor catalog               │
│                                                                 │
│  • IE3 efficiency trends by power class                         │
│  • Cross-manufacturer specification comparison                  │
│  • Data quality heatmap (field completeness by manufacturer)    │
│  • Conflict frequency report                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 9: EXPORT & INTEGRATION                  │
│  Downstream consumption of verified product intelligence        │
│                                                                 │
│  • Export to structured JSON / CSV / ERP-ready format           │
│  • REST API for product intelligence queries                    │
│  • Webhook notifications for new conflicts / resolutions        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Dependency Map

```
productiq.schema          ← imported by ALL other modules (never redefined)
    ↓
productiq.config          ← imported by llm, extraction, validation, enrichment
productiq.logging_setup   ← imported by all
    ↓
productiq.llm             ← imported by enrichment only
    ↓
productiq.extraction      → produces MotorProduct (all-Unknown → progressively filled)
productiq.normalization   → transforms FieldValue units
productiq.validation      → sets Conflicted where physics fails
productiq.enrichment      → fills Unknown with Inferred (LLM-grounded)
productiq.trust           → scores MotorProduct → TrustScore
productiq.dashboard       → renders MotorProduct + TrustScore for humans
```

---

## Data Flow: A Single Motor Record

```
1. PDFExtractor reads brochure table row
   → rated_power = FieldValue(value=1.1, unit="kW", status=Verified, sources=[pdf_src])
   → rated_speed = FieldValue(value=1455, unit="rpm", status=Verified, sources=[pdf_src])
   → ip_rating   = FieldValue(value=None, unit=None, status=Unknown, sources=[])
                   (not in table — preserved as Unknown, not guessed)

2. CSVExtractor reads legacy CSV row
   → rated_power = FieldValue(value=1.1, unit="kW", status=Inferred, sources=[csv_src])
                   (CSV is derived data → Inferred, not Verified)

3. Normalization: no-op for kW and rpm (already canonical)

4. Conflict detection: both sources agree rated_power=1.1 kW → status=Verified (no conflict)
   If sources disagreed: → status=Conflicted, both SourceEntries preserved

5. Validation: P = √3 × 400V × 7.22A × 0.59 PF × 0.83η ≈ 1.09 kW ≈ 1.1 kW ✓

6. Enrichment: ip_rating=Unknown → LLM queries: "WEG W22 Severe Process IP rating?"
   → ip_rating = FieldValue(value="IP56", status=Inferred, sources=[llm_src])

7. Trust score: completeness=9/11, source_diversity=pdf+csv, conflicts=0, validations_pass=1
   → overall_score = 0.87

8. Dashboard shows: 9 green (Verified/Inferred), 2 grey (Unknown), trust=87%
```

---

## Phase 0 Boundary (What Is and Is NOT Built)

| Component | Phase 0 Status |
|---|---|
| `productiq.schema` | ✅ COMPLETE — frozen, tested |
| `productiq.config` | ✅ COMPLETE |
| `productiq.logging_setup` | ✅ COMPLETE |
| `productiq.llm.client` | ✅ COMPLETE — connectivity proven |
| `productiq.extraction` | ✅ COMPLETE — PDFExtractor, CSVExtractor, WebExtractor implemented (Phase 1) |
| `productiq.normalization` | 🔲 STUB — BaseNormalizer interface only |
| `productiq.validation` | 🔲 STUB — BaseValidator interface only |
| `productiq.enrichment` | 🔲 STUB — BaseEnricher interface only |
| `productiq.trust` | 🔲 STUB — BaseTrustScorer + TrustScore dataclass |
| `productiq.dashboard` | 🔲 STUB — empty module boundary |

---

## Design Principles (Enforced Across All Phases)

1. **Schema is the single source of truth.** Import `MotorProduct`, `FieldValue`, `DataStatus` from `productiq.schema`. Never duplicate them.
2. **Immutable observations.** Once a `SourceEntry` is recorded, it is never deleted or overwritten.
3. **Conflict visibility.** A `Conflicted` field is a first-class product state, not an error to be hidden.
4. **Explainability over accuracy.** A score of 0.7 with a visible formula is more valuable than a score of 0.9 from a black box.
5. **Phase boundaries.** Each phase consumes the output of the previous phase. No phase should bypass the schema.
6. **Human authority.** The human review queue (Phase 7) is the only mechanism for converting `Conflicted` to `Verified`. LLM cannot do this.
