"""
ProductIQ Enrichment Prompts & Context Builder — Phase 4
========================================================
Versioned prompt templates and token-optimized context formatting.

Anti-hallucination contract:
- Only verified and normalized facts are presented as factual.
- Conflicts are explicitly flagged so the LLM does not fabricate a winner.
- Required JSON output schema is strictly described.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from productiq.normalization.models import NormalizedProduct, NormalizationOutcome
from productiq.validation.models import ProductValidationReport, ValidationStatus

PROMPT_VERSION = "4.0.0"

SYSTEM_PROMPT = """You are the ProductIQ AI Product Intelligence Engine for Industrial Commerce.
Your role is to transform verified, normalized, and validated industrial motor specifications into clear, high-value, commerce-ready product intelligence.

CRITICAL ANTI-HALLUCINATION & INTEGRITY RULES:
1. FACTUAL GROUNDING: Use ONLY the provided verified and normalized specifications. Never invent or assume missing electrical/mechanical ratings (e.g., kW, V, A, RPM, IP rating, weight).
2. NO SILENT CONFLICT RESOLUTION: If an attribute is marked as "CONFLICT", DO NOT pick a single winner or present one value as true. Explicitly state the disagreement in your analysis and note that verification is required.
3. CLAIM SEPARATION:
   - "source_backed_claims": Claims directly backed by extracted source evidence (e.g., "Delivers 1.1 kW output at 1455 rpm with IP56 protection").
   - "inferred_claims": Logical engineering deductions based on physics, standard categories, or applications (e.g., "Suitable for continuous duty in harsh, wet, or dusty environments due to IP56 enclosure").
4. REALISTIC APPLICATIONS: Recommend genuine industrial applications (pumps, fans, conveyors, compressors, agitators) suited to the specific power, torque, speed, and enclosure rating.
5. MISSING DATA HONESTY: Explicitly state what critical data is missing (e.g. if frequency or pole count is unverified).
6. CONCISE JSON ONLY: Respond with a compact, strictly valid JSON object matching the requested schema. No markdown fences, no conversational preamble. Keep string values crisp and informative.
"""


def build_enrichment_payload(
    product: NormalizedProduct,
    validation_report: ProductValidationReport,
) -> Dict[str, Any]:
    """
    Construct a compact, token-optimized context payload for the LLM.
    Separates verified facts, conflicts, unmapped evidence, and validation findings.
    """
    verified_fields: Dict[str, Any] = {}
    conflicted_fields: Dict[str, Any] = {}
    missing_fields: list[str] = []

    for name, nf in product.fields.items():
        if nf.outcome in (NormalizationOutcome.PASSTHROUGH, NormalizationOutcome.NORMALIZED):
            verified_fields[name] = {
                "value": nf.canonical_value,
                "unit": nf.canonical_unit,
                "sources": list(set(ev.source_type for ev in nf.evidence_refs)),
            }
        elif nf.outcome == NormalizationOutcome.CONFLICT:
            conflict_details = []
            for c in nf.conflicts:
                conflict_details.append({
                    "source_a": f"{c.source_a.source_type} ({c.source_a.attribute}): {c.value_a} {c.unit_a or ''}".strip(),
                    "source_b": f"{c.source_b.source_type} ({c.source_b.attribute}): {c.value_b} {c.unit_b or ''}".strip(),
                    "note": c.note,
                })
            conflicted_fields[name] = {
                "conflicts": conflict_details,
                "evidence_count": len(nf.evidence_refs),
            }
        elif nf.outcome == NormalizationOutcome.MISSING:
            missing_fields.append(name)

    # Useful unmapped evidence (e.g. torque, sound, inertia)
    unmapped_specs: Dict[str, Any] = {}
    for ev in product.unmapped_evidence:
        if ev.parsed_value is not None:
            unmapped_specs[ev.attribute] = {
                "value": ev.parsed_value,
                "unit": ev.raw_unit or "",
                "source": ev.source_type,
            }

    # Key validation findings
    val_summary = {
        "overall_status": validation_report.overall_status.value,
        "pass_count": validation_report.pass_count,
        "conflict_count": validation_report.conflict_count,
        "warning_count": validation_report.warning_count,
    }

    engineering_notes = []
    for f in validation_report.findings:
        if "ENGINEERING" in f.rule_id:
            engineering_notes.append(f"{f.rule_id}: [{f.status.value}] {f.explanation}")
        elif f.rule_id == "CONFLICT_RATED_CURRENT_PDF_VS_CSV":
            engineering_notes.append(f"KNOWN_CONFLICT: {f.explanation}")

    return {
        "product_id": product.product_id,
        "manufacturer": product.manufacturer,
        "model": product.model,
        "verified_specifications": verified_fields,
        "conflicted_specifications": conflicted_fields,
        "unmapped_specifications": unmapped_specs,
        "missing_fields": missing_fields,
        "validation_summary": val_summary,
        "validation_engineering_findings": engineering_notes,
    }


def build_user_prompt(payload: Dict[str, Any]) -> str:
    """Format the payload and JSON output requirements into the user prompt."""
    payload_json = json.dumps(payload, indent=2)

    return f"""Analyze the following validated motor product specifications and generate structured commercial intelligence:

INPUT DATA:
{payload_json}

OUTPUT INSTRUCTIONS:
Return a single JSON object with EXACTLY these fields (keep entries concise and high-density):
{{
  "summary": "2-3 concise sentences summarizing the motor for technical buyers.",
  "technical_description": "A focused technical description of the motor capabilities and specifications.",
  "key_selling_points": ["3-4 bullet points highlighting key strengths (efficiency, enclosure, reliability)."],
  "target_applications": ["4-5 specific industrial applications suited to this power/speed/enclosure rating."],
  "suggested_keywords": ["6-8 B2B search and catalog keywords."],
  "inferred_fields": {{
    "frequency": "50 Hz",
    "poles": 4
  }},
  "source_backed_claims": [
    {{
      "claim_text": "Factual statement directly supported by input data",
      "category": "performance",
      "field": "rated_power",
      "evidence_sources": ["pdf", "csv"],
      "confidence": 1.0
    }}
  ],
  "inferred_claims": [
    {{
      "claim_text": "Engineering inference or application guidance",
      "category": "application",
      "field": null,
      "evidence_sources": [],
      "confidence": 0.85,
      "notes": "Basis for inference"
    }}
  ],
  "unresolved_conflicts": [
    {{
      "field": "conflicted_field_name",
      "description": "Disagreement summary without picking a winner",
      "action_needed": "Verification required against manufacturer nameplate"
    }}
  ],
  "missing_information_notes": [
    "List of parameters missing from catalog records."
  ],
  "enrichment_warnings": [
    "Any warnings regarding conflicted data or limitations."
  ]
}}
"""
