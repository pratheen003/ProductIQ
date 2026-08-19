"""
ProductIQ Trust Evaluator — Phase 5
====================================
Deterministic, explainable trust evaluation engine for industrial product intelligence.

Key invariants:
1. Attribute trust is independently derived from Phase 2 normalization and Phase 3 validation.
2. Claim trust is evaluated from Phase 4 claims using provenance and validation status.
3. No silent conflict resolution: conflicted fields remain CONFLICTED and REVIEW_REQUIRED.
4. Review queue provides actionable, structured items with explicit WHAT, WHY, and ACTION.
5. Trust scores are computed mathematically with visible formulas.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from productiq.schema.motor import CANONICAL_UNITS
from productiq.normalization.models import (
    NormalizedProduct,
    NormalizedField,
    NormalizationOutcome,
    ConflictRecord,
)
from productiq.validation.models import (
    ProductValidationReport,
    ValidationFinding,
    ValidationStatus,
)
from productiq.enrichment.models import (
    ProductEnrichment,
    EnrichmentClaim,
)
from productiq.trust.models import (
    TrustStatus,
    PublishabilityStatus,
    AttributeTrustResult,
    ClaimTrustResult,
    ReviewItem,
    ProductTrustReport,
)


class MotorTrustEvaluator:
    """
    Evaluates motor product intelligence across attributes, claims, and overall publishability.
    """

    # Weights for deterministic trust scoring
    WEIGHT_COMPLETENESS = 0.35
    WEIGHT_VALIDITY     = 0.35
    WEIGHT_DIVERSITY    = 0.30
    CONFLICT_PENALTY_PER_FIELD = 0.15

    def __init__(self):
        pass

    def evaluate(
        self,
        normalized_product: Optional[NormalizedProduct],
        validation_report: Optional[ProductValidationReport],
        enrichment: Optional[ProductEnrichment] = None,
        product_id: Optional[str] = None,
        manufacturer: str = "WEG",
        model: str = "W22",
    ) -> ProductTrustReport:
        """
        Produce a complete ProductTrustReport by analyzing normalization, validation, and enrichment.
        """
        pid = product_id or (normalized_product.product_id if normalized_product else "UNKNOWN")
        mfg = manufacturer or (normalized_product.manufacturer if normalized_product else "WEG")
        mdl = model or (normalized_product.model if normalized_product else "W22")

        # 1. Attribute-Level Trust Evaluation
        attribute_trust, conflicted_fields, field_review_items = self._evaluate_attributes(
            pid, normalized_product, validation_report, enrichment
        )

        # 2. Claim-Level Trust Evaluation
        claim_trust, claim_review_items = self._evaluate_claims(
            pid, enrichment, conflicted_fields
        )

        # 3. Validation Finding Review Items
        val_review_items = self._extract_validation_review_items(pid, validation_report)

        # Combine review items (deduplicated by review_id)
        all_review_items = self._combine_review_items(field_review_items + claim_review_items + val_review_items)

        # 4. Compute Publishable vs Restricted Attributes
        publishable_attrs = [
            f for f, res in attribute_trust.items()
            if res.publishability in (PublishabilityStatus.PUBLISHABLE, PublishabilityStatus.PUBLISHABLE_WITH_WARNING)
        ]
        restricted_attrs = [
            f for f, res in attribute_trust.items()
            if res.publishability in (PublishabilityStatus.REVIEW_REQUIRED, PublishabilityStatus.NOT_PUBLISHABLE)
        ]

        # 5. Compute Deterministic Mathematical Trust Score
        trust_score, breakdown, formula = self._compute_trust_score(
            attribute_trust, validation_report, normalized_product, len(conflicted_fields)
        )

        # 6. Overall Product Trust & Publishability
        overall_status, overall_pub, summary_reason = self._determine_overall_status(
            attribute_trust, conflicted_fields, all_review_items, trust_score
        )

        # 7. Unresolved Conflicts List
        unresolved_conflicts = []
        if enrichment and enrichment.unresolved_conflicts:
            unresolved_conflicts = enrichment.unresolved_conflicts
        elif normalized_product:
            for fname, nfield in normalized_product.fields.items():
                if nfield.conflicts:
                    for c in nfield.conflicts:
                        unresolved_conflicts.append({
                            "field": fname,
                            "description": f"CONFLICT: Source A ({c.source_a.source_type}) reports {c.value_a} {c.unit_a or ''} vs Source B ({c.source_b.source_type}) reports {c.value_b} {c.unit_b or ''}.",
                            "action_needed": "Physical nameplate or engineering drawing verification required.",
                        })

        metadata = {
            "evaluator_version": "5.0.0",
            "has_normalization": normalized_product is not None,
            "has_validation": validation_report is not None,
            "has_enrichment": enrichment is not None,
            "total_attributes_evaluated": len(attribute_trust),
            "total_claims_evaluated": len(claim_trust),
            "conflicted_fields_count": len(conflicted_fields),
        }

        return ProductTrustReport(
            product_id=pid,
            manufacturer=mfg,
            model=mdl,
            overall_trust_status=overall_status,
            overall_publishability=overall_pub,
            trust_score=trust_score,
            trust_score_formula=formula,
            trust_score_breakdown=breakdown,
            attribute_trust=attribute_trust,
            claim_trust=claim_trust,
            review_queue=all_review_items,
            unresolved_conflicts=unresolved_conflicts,
            publishable_attributes=publishable_attrs,
            restricted_attributes=restricted_attrs,
            summary_reason=summary_reason,
            metadata=metadata,
        )

    # -----------------------------------------------------------------------
    # Attribute Trust
    # -----------------------------------------------------------------------

    def _evaluate_attributes(
        self,
        product_id: str,
        norm: Optional[NormalizedProduct],
        val: Optional[ProductValidationReport],
        enrich: Optional[ProductEnrichment],
    ) -> Tuple[Dict[str, AttributeTrustResult], Set[str], List[ReviewItem]]:
        """
        Evaluate each canonical field independently from normalization and validation.
        """
        results: Dict[str, AttributeTrustResult] = {}
        conflicted_fields: Set[str] = set()
        review_items: List[ReviewItem] = []

        # Index validation findings by field
        findings_by_field: Dict[str, List[ValidationFinding]] = {}
        if val and val.findings:
            for f in val.findings:
                if f.field:
                    findings_by_field.setdefault(f.field, []).append(f)

        inferred_fields = enrich.inferred_fields if enrich else {}

        for field_name, canonical_unit in CANONICAL_UNITS.items():
            norm_field: Optional[NormalizedField] = norm.fields.get(field_name) if norm else None
            field_findings = findings_by_field.get(field_name, [])
            rule_ids = [f.rule_id for f in field_findings]

            # Collect evidence references from normalization
            evidence_sources: List[str] = []
            if norm_field:
                for ref in norm_field.evidence_refs:
                    src_str = f"{ref.source_type}"
                    if ref.page is not None:
                        src_str += f":p.{ref.page}"
                    elif ref.row is not None:
                        src_str += f":row.{ref.row}"
                    if ref.attribute:
                        src_str += f" ({ref.attribute})"
                    if src_str not in evidence_sources:
                        evidence_sources.append(src_str)

            # Check for conflict in Phase 2 or Phase 3
            is_conflicted = False
            if norm_field and (norm_field.outcome == NormalizationOutcome.CONFLICT or len(norm_field.conflicts) > 0):
                is_conflicted = True
            for f in field_findings:
                if f.status == ValidationStatus.CONFLICT:
                    is_conflicted = True

            if is_conflicted:
                conflicted_fields.add(field_name)
                # Build conflict explanation & source breakdown
                conflict_details: List[Dict[str, Any]] = []
                reason_parts = []
                if norm_field and norm_field.conflicts:
                    for c in norm_field.conflicts:
                        conflict_details.append({
                            "source_a": c.source_a.source_type,
                            "value_a": c.value_a,
                            "unit_a": c.unit_a,
                            "raw_a": c.source_a.raw_value,
                            "source_b": c.source_b.source_type,
                            "value_b": c.value_b,
                            "unit_b": c.unit_b,
                            "raw_b": c.source_b.raw_value,
                        })
                        reason_parts.append(
                            f"Source disagreement: {c.source_a.source_type} reports {c.value_a} {c.unit_a or ''} vs {c.source_b.source_type} reports {c.value_b} {c.unit_b or ''}"
                        )
                reason_str = "; ".join(reason_parts) if reason_parts else f"Multi-source conflict detected on '{field_name}'."
                reason_full = f"CONFLICT: {reason_str}. No single winner picked — resolution requires human review."

                results[field_name] = AttributeTrustResult(
                    field=field_name,
                    canonical_value=norm_field.canonical_value if norm_field else None,
                    canonical_unit=canonical_unit,
                    trust_status=TrustStatus.CONFLICTED,
                    publishability=PublishabilityStatus.REVIEW_REQUIRED,
                    validation_status=ValidationStatus.CONFLICT.value,
                    is_conflicted=True,
                    evidence_sources=evidence_sources,
                    confidence_score=0.30,
                    reason=reason_full,
                    validation_rule_ids=rule_ids,
                )

                # Generate Review Item
                review_items.append(ReviewItem(
                    review_id=f"REV-{product_id}-{field_name}-conflict",
                    target_type="attribute",
                    target_name=field_name,
                    severity="HIGH",
                    issue_type="CONFLICT",
                    description=f"Field '{field_name}' has conflicting values from multiple authoritative sources.",
                    conflicting_values=conflict_details,
                    validation_rule_id="CONFLICT_CROSS_SOURCE",
                    recommended_action=f"Inspect physical nameplate or official dimension drawing to resolve '{field_name}'.",
                ))
                continue

            # Check if field has validation failure
            has_fail = any(f.status == ValidationStatus.FAIL for f in field_findings)
            if has_fail:
                fail_finding = next(f for f in field_findings if f.status == ValidationStatus.FAIL)
                results[field_name] = AttributeTrustResult(
                    field=field_name,
                    canonical_value=norm_field.canonical_value if norm_field else None,
                    canonical_unit=canonical_unit,
                    trust_status=TrustStatus.UNSUPPORTED,
                    publishability=PublishabilityStatus.NOT_PUBLISHABLE,
                    validation_status=ValidationStatus.FAIL.value,
                    is_conflicted=False,
                    evidence_sources=evidence_sources,
                    confidence_score=0.10,
                    reason=f"Validation failed: {fail_finding.explanation}",
                    validation_rule_ids=rule_ids,
                )
                review_items.append(ReviewItem(
                    review_id=f"REV-{product_id}-{field_name}-fail",
                    target_type="attribute",
                    target_name=field_name,
                    severity="HIGH",
                    issue_type="FAIL",
                    description=f"Field '{field_name}' failed validation check '{fail_finding.rule_id}': {fail_finding.explanation}",
                    validation_rule_id=fail_finding.rule_id,
                    recommended_action="Correct input data or adjust equipment specification.",
                ))
                continue

            # Check if field has validation warning
            has_warning = any(f.status == ValidationStatus.WARNING for f in field_findings)
            if has_warning:
                warn_finding = next(f for f in field_findings if f.status == ValidationStatus.WARNING)
                results[field_name] = AttributeTrustResult(
                    field=field_name,
                    canonical_value=norm_field.canonical_value if norm_field else None,
                    canonical_unit=canonical_unit,
                    trust_status=TrustStatus.REVIEW_REQUIRED,
                    publishability=PublishabilityStatus.PUBLISHABLE_WITH_WARNING,
                    validation_status=ValidationStatus.WARNING.value,
                    is_conflicted=False,
                    evidence_sources=evidence_sources,
                    confidence_score=0.75,
                    reason=f"Validation warning: {warn_finding.explanation}",
                    validation_rule_ids=rule_ids,
                )
                review_items.append(ReviewItem(
                    review_id=f"REV-{product_id}-{field_name}-warning",
                    target_type="attribute",
                    target_name=field_name,
                    severity="MEDIUM",
                    issue_type="WARNING",
                    description=f"Field '{field_name}' flagged warning by rule '{warn_finding.rule_id}': {warn_finding.explanation}",
                    validation_rule_id=warn_finding.rule_id,
                    recommended_action="Verify specification boundaries before catalog publishing.",
                ))
                continue

            # Check if field is present and verified in Phase 2
            if norm_field and norm_field.canonical_value is not None and norm_field.outcome in (NormalizationOutcome.PASSTHROUGH, NormalizationOutcome.NORMALIZED):
                results[field_name] = AttributeTrustResult(
                    field=field_name,
                    canonical_value=norm_field.canonical_value,
                    canonical_unit=canonical_unit,
                    trust_status=TrustStatus.TRUSTED,
                    publishability=PublishabilityStatus.PUBLISHABLE,
                    validation_status=ValidationStatus.PASS.value if field_findings else "PASS",
                    is_conflicted=False,
                    evidence_sources=evidence_sources,
                    confidence_score=1.0,
                    reason="Verified from manufacturer source evidence and passed all validation checks.",
                    validation_rule_ids=rule_ids,
                )
                continue

            # Check if field is inferred in Phase 4
            if field_name in inferred_fields:
                inferred_val = inferred_fields[field_name]
                results[field_name] = AttributeTrustResult(
                    field=field_name,
                    canonical_value=inferred_val,
                    canonical_unit=canonical_unit,
                    trust_status=TrustStatus.UNVERIFIED,
                    publishability=PublishabilityStatus.PUBLISHABLE_WITH_WARNING,
                    validation_status="NOT_CHECKED",
                    is_conflicted=False,
                    evidence_sources=["llm-enrichment"],
                    confidence_score=0.70,
                    reason=f"Parameter '{field_name}' is an AI-grounded inference ({inferred_val}). Not directly extracted from datasheet tables.",
                    validation_rule_ids=rule_ids,
                )
                continue

            # Field is missing
            results[field_name] = AttributeTrustResult(
                field=field_name,
                canonical_value=None,
                canonical_unit=canonical_unit,
                trust_status=TrustStatus.MISSING,
                publishability=PublishabilityStatus.NOT_PUBLISHABLE,
                validation_status=ValidationStatus.NOT_CHECKED.value,
                is_conflicted=False,
                evidence_sources=[],
                confidence_score=0.0,
                reason=f"Parameter '{field_name}' is missing across all ingested sources.",
                validation_rule_ids=rule_ids,
            )

        return results, conflicted_fields, review_items

    # -----------------------------------------------------------------------
    # Claim Trust
    # -----------------------------------------------------------------------

    def _evaluate_claims(
        self,
        product_id: str,
        enrichment: Optional[ProductEnrichment],
        conflicted_fields: Set[str],
    ) -> Tuple[List[ClaimTrustResult], List[ReviewItem]]:
        """
        Evaluate AI enrichment claims against source evidence and conflicted attributes.
        """
        claims: List[ClaimTrustResult] = []
        review_items: List[ReviewItem] = []

        if not enrichment:
            return claims, review_items

        # 1. Source-backed claims
        for claim in enrichment.source_backed_claims:
            is_associated_conflict = claim.field in conflicted_fields if claim.field else False

            if is_associated_conflict:
                claims.append(ClaimTrustResult(
                    claim_text=claim.claim_text,
                    category=claim.category,
                    claim_type="SOURCE_BACKED",
                    trust_status=TrustStatus.CONFLICTED,
                    publishability=PublishabilityStatus.REVIEW_REQUIRED,
                    supporting_fields=[claim.field] if claim.field else [],
                    evidence_sources=claim.evidence_sources,
                    confidence=0.40,
                    reason=f"Claim touches field '{claim.field}' which has unresolved multi-source conflicts.",
                ))
                review_items.append(ReviewItem(
                    review_id=f"REV-{product_id}-claim-{claim.category}-conflict",
                    target_type="claim",
                    target_name=claim.field or claim.category,
                    severity="HIGH",
                    issue_type="CONFLICT",
                    description=f"AI claim '{claim.claim_text}' references conflicted specification '{claim.field}'.",
                    affected_claims=[claim.claim_text],
                    recommended_action="Do not publish claim as uncontested fact until specification conflict is resolved.",
                ))
            else:
                claims.append(ClaimTrustResult(
                    claim_text=claim.claim_text,
                    category=claim.category,
                    claim_type="SOURCE_BACKED",
                    trust_status=TrustStatus.TRUSTED,
                    publishability=PublishabilityStatus.PUBLISHABLE,
                    supporting_fields=[claim.field] if claim.field else [],
                    evidence_sources=claim.evidence_sources,
                    confidence=claim.confidence,
                    reason="Ground truth verified from manufacturer datasheets and catalog records.",
                ))

        # 2. Inferred claims
        for claim in enrichment.inferred_claims:
            claims.append(ClaimTrustResult(
                claim_text=claim.claim_text,
                category=claim.category,
                claim_type="INFERRED",
                trust_status=TrustStatus.UNVERIFIED,
                publishability=PublishabilityStatus.PUBLISHABLE_WITH_WARNING,
                supporting_fields=[claim.field] if claim.field else [],
                evidence_sources=claim.evidence_sources,
                confidence=claim.confidence,
                reason=f"Inferred by LLM reasoning ({claim.notes or 'domain heuristic'}). Safe for catalog search with inferred disclaimer.",
            ))

        return claims, review_items

    # -----------------------------------------------------------------------
    # Validation Review Items
    # -----------------------------------------------------------------------

    def _extract_validation_review_items(
        self,
        product_id: str,
        val: Optional[ProductValidationReport],
    ) -> List[ReviewItem]:
        items: List[ReviewItem] = []
        if not val or not val.findings:
            return items

        for finding in val.findings:
            if finding.status == ValidationStatus.CONFLICT:
                # Handled via attribute evaluation
                pass
            elif finding.status == ValidationStatus.FAIL:
                items.append(ReviewItem(
                    review_id=f"REV-{product_id}-{finding.rule_id}",
                    target_type="validation",
                    target_name=finding.field or finding.rule_id,
                    severity="CRITICAL" if finding.severity == "CRITICAL" else "HIGH",
                    issue_type="FAIL",
                    description=f"Validation check '{finding.rule_id}' failed: {finding.explanation}",
                    validation_rule_id=finding.rule_id,
                    recommended_action="Inspect product engineering constraints and correct erroneous raw data.",
                ))
            elif finding.status == ValidationStatus.WARNING:
                items.append(ReviewItem(
                    review_id=f"REV-{product_id}-{finding.rule_id}",
                    target_type="validation",
                    target_name=finding.field or finding.rule_id,
                    severity="MEDIUM",
                    issue_type="WARNING",
                    description=f"Validation warning on rule '{finding.rule_id}': {finding.explanation}",
                    validation_rule_id=finding.rule_id,
                    recommended_action="Review physical boundary parameters.",
                ))

        return items

    def _combine_review_items(self, items: List[ReviewItem]) -> List[ReviewItem]:
        seen = set()
        unique = []
        for it in items:
            if it.review_id not in seen:
                seen.add(it.review_id)
                unique.append(it)
        return unique

    # -----------------------------------------------------------------------
    # Deterministic Trust Scoring Formula
    # -----------------------------------------------------------------------

    def _compute_trust_score(
        self,
        attribute_trust: Dict[str, AttributeTrustResult],
        val: Optional[ProductValidationReport],
        norm: Optional[NormalizedProduct],
        conflict_count: int,
    ) -> Tuple[float, Dict[str, float], str]:
        """
        Compute transparent, deterministic mathematical trust score.
        S = clamp(w_c * Completeness + w_v * Validity + w_d * Diversity - ConflictPenalty, 0.0, 1.0)
        """
        total_attrs = len(attribute_trust)
        if total_attrs == 0:
            return 0.0, {}, "Score = 0.0"

        # 1. Completeness Score (non-MISSING fields ratio)
        non_missing = sum(1 for a in attribute_trust.values() if a.trust_status != TrustStatus.MISSING)
        completeness = non_missing / total_attrs

        # 2. Validity Score (PASS rate of attempted validation checks)
        validity = 1.0
        if val and val.findings and len(val.findings) > 0:
            total_checks = len(val.findings) - val.not_checked_count
            if total_checks > 0:
                pass_count = val.pass_count
                warn_count = val.warning_count
                # Warnings count as 0.75 pass
                validity = min(1.0, (pass_count + 0.75 * warn_count) / total_checks)

        # 3. Source Diversity Score (sources contributing to product)
        diversity = 0.50
        if norm:
            all_source_types = set()
            for nf in norm.fields.values():
                for ref in nf.evidence_refs:
                    all_source_types.add(ref.source_type)
            if len(all_source_types) >= 2:
                diversity = 1.0
            elif len(all_source_types) == 1:
                diversity = 0.75
            else:
                diversity = 0.30

        # 4. Conflict Penalty
        conflict_penalty = min(0.50, conflict_count * self.CONFLICT_PENALTY_PER_FIELD)

        # 5. Composite Score
        raw_score = (
            self.WEIGHT_COMPLETENESS * completeness +
            self.WEIGHT_VALIDITY * validity +
            self.WEIGHT_DIVERSITY * diversity -
            conflict_penalty
        )
        final_score = max(0.0, min(1.0, raw_score))

        breakdown = {
            "completeness_score": completeness,
            "validity_score": validity,
            "diversity_score": diversity,
            "conflict_penalty": conflict_penalty,
            "completeness_weight": self.WEIGHT_COMPLETENESS,
            "validity_weight": self.WEIGHT_VALIDITY,
            "diversity_weight": self.WEIGHT_DIVERSITY,
        }

        formula_str = (
            f"TrustScore = clamp({self.WEIGHT_COMPLETENESS}*Completeness({completeness:.2f}) + "
            f"{self.WEIGHT_VALIDITY}*Validity({validity:.2f}) + "
            f"{self.WEIGHT_DIVERSITY}*Diversity({diversity:.2f}) - "
            f"ConflictPenalty({conflict_penalty:.2f}), 0.0, 1.0) = {final_score:.4f}"
        )

        return final_score, breakdown, formula_str

    # -----------------------------------------------------------------------
    # Overall Status & Publishability
    # -----------------------------------------------------------------------

    def _determine_overall_status(
        self,
        attrs: Dict[str, AttributeTrustResult],
        conflicted_fields: Set[str],
        review_items: List[ReviewItem],
        trust_score: float,
    ) -> Tuple[TrustStatus, PublishabilityStatus, str]:
        """
        Determine product-level trust status and commercial publishability.
        """
        has_critical_fail = any(it.severity in ("CRITICAL", "HIGH") and it.issue_type == "FAIL" for it in review_items)
        has_conflict = len(conflicted_fields) > 0

        if has_conflict:
            return (
                TrustStatus.CONFLICTED,
                PublishabilityStatus.REVIEW_REQUIRED,
                f"Product has {len(conflicted_fields)} unresolved multi-source conflict(s) ({', '.join(sorted(conflicted_fields))}). Human engineering review required before publication."
            )

        if has_critical_fail:
            return (
                TrustStatus.UNSUPPORTED,
                PublishabilityStatus.NOT_PUBLISHABLE,
                "Product contains failed engineering or physical range validation checks. Blocked from publication."
            )

        has_warnings = any(it.issue_type == "WARNING" for it in review_items)
        if has_warnings:
            return (
                TrustStatus.REVIEW_REQUIRED,
                PublishabilityStatus.PUBLISHABLE_WITH_WARNING,
                "Product passed primary validation but contains non-critical warnings. Publishable with warning disclaimer."
            )

        if trust_score >= 0.80:
            return (
                TrustStatus.TRUSTED,
                PublishabilityStatus.PUBLISHABLE,
                "All critical specifications verified from manufacturer datasheets with zero conflicts. Fully publishable for commercial catalogs."
            )

        return (
            TrustStatus.UNVERIFIED,
            PublishabilityStatus.PUBLISHABLE_WITH_WARNING,
            "Product specifications are partially complete with grounded inferences. Publishable with informational disclaimer."
        )
