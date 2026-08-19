# Phase 4 — AI Enrichment Layer (Groq Provider)

## Objective

Transform validated, provenance-backed industrial motor evidence from Phase 2 (Normalization) and Phase 3 (Validation) into structured, commerce-ready commercial intelligence using grounded LLM reasoning while strictly preserving factual boundaries, source provenance, and multi-source conflicts.

**Phase 4 is NOT:**
- A generic "call an LLM" wrapper
- An arbitrary halluncination engine
- A conflict-resolution shortcut that silently picks a winner
- An ungrounded marketing copy generator

**Phase 4 IS:**
- A validation-aware, provider-agnostic product intelligence engine
- A strict separator of source-backed facts vs. grounded inferences
- A guardian of unresolved conflicts (e.g., PDF 2.34 A vs CSV 7.22 A)
- A generator of commerce-ready summaries, technical descriptions, application suggestions, keywords, and inferred metadata

---

## Provider Migration & Multi-Provider Architecture

### Context
During Phase 0, OpenAI was initially integrated as the baseline LLM provider. When OpenAI quota credits were exhausted, **Groq** was integrated as the primary, fast, free-tier hackathon development provider.

### Architecture
ProductIQ business logic interacts exclusively with the abstract `LLMClient`:

```
ProductIQ Business Logic (MotorEnricher / BatchEnricher)
                          ↓
                      LLMClient
                          ↓
              ┌───────────────────────┐
              │  Provider Abstraction │
              └───────────┬───────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
      Groq API (Primary)        OpenAI API (Optional)
    (openai/gpt-oss-20b)           (gpt-4o-mini)
```

- **Zero Vendor Lock-In:** Swapping between Groq and OpenAI requires changing only `.env` (`LLM_PROVIDER=groq` or `LLM_PROVIDER=openai`).
- **Security Guarantee:** API keys are never logged, never printed, never stored in JSON outputs, and never committed to Git.

---

## Status & Metrics

| Metric | Value |
|---|---|
| **Phase 4 Status** | ✅ COMPLETE |
| **Products Enriched** | 12 / 12 (100%) |
| **LLM Provider** | Groq (`openai/gpt-oss-20b`) |
| **Prompt Version** | `4.0.0` |
| **Total Enriched Claims Generated** | 120+ structured claims |
| **Source-Backed Claims** | Tagged with `is_source_backed=True` and evidence refs |
| **Inferred Claims** | Tagged with `is_source_backed=False` and confidence scores |
| **Conflicts Preserved** | 100% of Phase 3 conflicts surfaced without picking winners |
| **Tests** | All tests passed (mocked by default + optional live Groq test) |
| **Phase 4 Verification** | 18 / 18 checks passed |

---

## Anti-Hallucination Contract

ProductIQ's core philosophy is that AI must enhance product data without polluting truth. The Phase 4 engine enforces the following contractual guarantees:

1. **Deterministic Grounding:** All verified parameters in `source_backed_claims` trace to Phase 2 normalized fields and Phase 1 source evidence.
2. **Strict Status Tiering:** Inferred fields (such as nominal frequency `50 Hz` or pole count `4`) written to Phase 0 `MotorProduct` are strictly assigned `DataStatus.INFERRED` (never `DataStatus.VERIFIED`).
3. **No Silent Conflict Resolution:** If Phase 3 flagged a conflict (such as `rated_current` with 2.34 A in PDF vs 7.22 A in CSV), Phase 4:
   - Preserves both conflicting values in `unresolved_conflicts`
   - Generates an explicit `enrichment_warning`
   - Never allows the LLM to pick one number as an uncontested fact
4. **Structured Output Enforcement:** The model must return typed, validated JSON conforming to the `ProductEnrichment` dataclass.

---

## Concrete Example: Known Conflict Preservation

For demo product `PIQ-W22SP-4P-1.1`:

```json
{
  "product_id": "PIQ-W22SP-4P-1.1",
  "summary": "The WEG W22 Severe Process 1.1 kW motor is an industrial 4-pole cast iron motor delivering 1455 rpm in severe operating environments.",
  "inferred_fields": {
    "frequency": "50 Hz",
    "poles": 4
  },
  "unresolved_conflicts": [
    {
      "field": "rated_current",
      "description": "CONFLICT: PDF reports 2.34 A while legacy CSV reports 7.22 A (matching full-load torque 7.22 Nm).",
      "action_needed": "Physical nameplate or engineering drawing verification required."
    }
  ],
  "enrichment_warnings": [
    "Unresolved multi-source conflict detected in 'rated_current'."
  ]
}
```

---

## Provenance Chain Through Phase 4

```
Original Source (PDF Page 5 / CSV Row 5)
                ↓
Phase 1 EvidenceRecord (raw_value="1.1", raw_unit="kW", page=5)
                ↓
Phase 2 NormalizedField (canonical_value=1.1, canonical_unit="kW", outcome="passthrough")
                ↓
Phase 3 ValidationFinding (rule="RANGE_RATED_POWER_POSITIVE", status="PASS")
                ↓
Phase 4 EnrichmentClaim (claim="Rated mechanical power output of 1.1 kW", is_source_backed=True)
                ↓
Phase 4 MotorProduct.frequency (status=DataStatus.INFERRED, source_id="llm-enrichment-groq")
```

Every statement produced by the AI is auditable back to its exact origin.

---

## Verification & Test Execution

```bash
# Run Phase 4 automated verification audit
python -X utf8 scripts/verify_phase4.py

# Run unit and integration tests
python -m pytest tests/test_phase4.py -v
```

---

## Phase 5 Handoff: Next Steps

Phase 5 will implement **Explainable Trust Scoring** (`productiq/trust/`):
1. Ingest `ProductEnrichment`, `ProductValidationReport`, `NormalizedProduct`, and Phase 1 `EvidenceRecord` items.
2. Calculate transparent mathematical trust scores ($S_{\text{overall}} = w_c S_{\text{completeness}} + w_v S_{\text{validity}} + w_d S_{\text{diversity}} - P_{\text{conflict}}$).
3. Display the exact scoring formula and penalty breakdown for every motor product.

**Phase 5 Boundary:** Phase 5 is NOT started.
