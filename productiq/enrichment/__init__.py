"""
ProductIQ Enrichment Module
---------------------------
Phase 4 target: LLM-grounded enrichment of GENUINELY missing fields only.

Rules (non-negotiable):
- Only enrich fields with status=Unknown after extraction + normalization
- Never overwrite a Verified or Inferred field with LLM output
- LLM output is ALWAYS marked status=Inferred, never Verified
- Every enriched field must cite the LLM model, prompt version, and timestamp
  as a SourceEntry (source_type="llm")
- Enrichment is grounded: LLM must cite manufacturer documentation, not hallucinate
- Never fabricate manufacturer names, model numbers, or catalog references

PHASE 0 STATUS: Stub only. LLM connectivity is proven in Phase 0,
but enrichment logic is NOT implemented until Phase 4.
"""
