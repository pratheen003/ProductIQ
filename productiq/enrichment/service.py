"""
ProductIQ AI Enrichment Service — Phase 4
=========================================
Orchestrates LLM-powered product intelligence generation while enforcing
anti-hallucination boundaries, conflict preservation, and provenance tracking.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from productiq.config import Config, load_config
from productiq.llm.client import LLMClient
from productiq.normalization.models import NormalizedProduct, NormalizationOutcome
from productiq.schema.motor import MotorProduct, DataStatus, FieldValue, SourceEntry, SourceType
from productiq.validation.models import ProductValidationReport, ValidationStatus
from productiq.enrichment.models import (
    EnrichmentClaim,
    ProductEnrichment,
    BatchEnrichmentReport,
)
from productiq.enrichment.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_enrichment_payload,
    build_user_prompt,
)

logger = logging.getLogger("productiq.enrichment")


class MotorEnricher:
    """
    Transforms validated product intelligence into structured commerce-ready
    content via grounded LLM reasoning.
    """

    def __init__(self, client: Optional[LLMClient] = None, config: Optional[Config] = None):
        self._config = config or load_config()
        self._client = client or LLMClient(self._config)

    @property
    def client(self) -> LLMClient:
        return self._client

    def enrich(
        self,
        product: NormalizedProduct,
        validation_report: ProductValidationReport,
    ) -> ProductEnrichment:
        """
        Generate AI enrichment for a single product based on normalized specifications
        and validation findings.
        """
        logger.info("Enriching product %s via %s (%s)...", product.product_id, self._client.provider, self._client.model)

        payload = build_enrichment_payload(product, validation_report)
        user_prompt = build_user_prompt(payload)

        # Call LLM via structured JSON interface
        raw_response = self._client.call_json(prompt=user_prompt, system=SYSTEM_PROMPT)

        # Parse into structured ProductEnrichment model
        enrichment = self._parse_and_validate_response(
            raw_response=raw_response,
            product=product,
            validation_report=validation_report,
        )

        logger.info(
            "Enrichment complete for %s | claims=%d (source_backed=%d, inferred=%d) | conflicts_preserved=%d",
            product.product_id,
            enrichment.total_claims,
            len(enrichment.source_backed_claims),
            len(enrichment.inferred_claims),
            len(enrichment.unresolved_conflicts),
        )
        return enrichment

    def enrich_motor_product(
        self,
        motor: MotorProduct,
        enrichment: ProductEnrichment,
    ) -> MotorProduct:
        """
        Update a Phase 0 MotorProduct with grounded inferences from enrichment.
        Only fields currently with DataStatus.UNKNOWN are updated, and they are
        strictly assigned DataStatus.INFERRED (never DataStatus.VERIFIED).
        """
        llm_source = SourceEntry(
            source_id=f"llm-enrichment-{enrichment.provider}",
            source_type=SourceType.WEB,  # closest enum match in frozen schema
            location=f"prompt_version_{enrichment.prompt_version}",
            reference=f"model={enrichment.model};timestamp={enrichment.generated_at}",
        )

        # Update frequency if inferred and currently Unknown
        if "frequency" in enrichment.inferred_fields and motor.frequency.status == DataStatus.UNKNOWN:
            freq_raw = str(enrichment.inferred_fields["frequency"])
            freq_val = 50.0 if "50" in freq_raw else (60.0 if "60" in freq_raw else None)
            if freq_val is not None:
                motor.frequency = FieldValue(
                    value=freq_val,
                    unit="Hz",
                    status=DataStatus.INFERRED,
                    confidence=0.90,
                    sources=[llm_source],
                )

        # Update poles if inferred and currently Unknown
        if "poles" in enrichment.inferred_fields and motor.poles.status == DataStatus.UNKNOWN:
            pole_raw = str(enrichment.inferred_fields["poles"])
            try:
                pole_val = int("".join(filter(str.isdigit, pole_raw)))
                if pole_val in (2, 4, 6, 8):
                    motor.poles = FieldValue(
                        value=pole_val,
                        unit=None,
                        status=DataStatus.INFERRED,
                        confidence=0.95,
                        sources=[llm_source],
                    )
            except ValueError:
                pass

        return motor

    def _parse_and_validate_response(
        self,
        raw_response: dict,
        product: NormalizedProduct,
        validation_report: ProductValidationReport,
    ) -> ProductEnrichment:
        """
        Validate LLM response and apply anti-hallucination post-processing:
        - Ensure all Phase 3 conflicts are preserved.
        - Validate claims format.
        - Attach evidence provenance.
        """
        summary = str(raw_response.get("summary", "")).strip()
        technical_description = str(raw_response.get("technical_description", "")).strip()
        key_selling_points = [str(x).strip() for x in raw_response.get("key_selling_points", []) if str(x).strip()]
        target_applications = [str(x).strip() for x in raw_response.get("target_applications", []) if str(x).strip()]
        suggested_keywords = [str(x).strip() for x in raw_response.get("suggested_keywords", []) if str(x).strip()]
        inferred_fields = raw_response.get("inferred_fields", {})
        missing_notes = [str(x).strip() for x in raw_response.get("missing_information_notes", []) if str(x).strip()]
        warnings = [str(x).strip() for x in raw_response.get("enrichment_warnings", []) if str(x).strip()]

        # Parse claims
        source_backed_claims: List[EnrichmentClaim] = []
        for c in raw_response.get("source_backed_claims", []):
            if isinstance(c, dict) and "claim_text" in c:
                source_backed_claims.append(EnrichmentClaim(
                    claim_text=str(c["claim_text"]),
                    category=str(c.get("category", "specification")),
                    field=c.get("field"),
                    is_source_backed=True,
                    evidence_sources=c.get("evidence_sources", ["normalized_evidence"]),
                    confidence=float(c.get("confidence", 1.0)),
                    notes=c.get("notes"),
                ))

        inferred_claims: List[EnrichmentClaim] = []
        for c in raw_response.get("inferred_claims", []):
            if isinstance(c, dict) and "claim_text" in c:
                inferred_claims.append(EnrichmentClaim(
                    claim_text=str(c["claim_text"]),
                    category=str(c.get("category", "application")),
                    field=c.get("field"),
                    is_source_backed=False,
                    evidence_sources=c.get("evidence_sources", []),
                    confidence=float(c.get("confidence", 0.85)),
                    notes=c.get("notes", "LLM inference"),
                ))

        # Conflict preservation: Ensure all conflicts from Phase 2 / Phase 3 are documented
        unresolved_conflicts = list(raw_response.get("unresolved_conflicts", []))

        # Check for any Phase 3 conflicts that might have been omitted by the LLM
        for f in validation_report.findings:
            if f.status == ValidationStatus.CONFLICT:
                conflict_field = f.field
                already_present = any(
                    isinstance(uc, dict) and uc.get("field") == conflict_field
                    for uc in unresolved_conflicts
                )
                if not already_present:
                    unresolved_conflicts.append({
                        "field": conflict_field,
                        "description": f.explanation,
                        "action_needed": "Requires physical nameplate or engineering drawing verification.",
                    })
                    warnings.append(f"Unresolved multi-source conflict detected in '{conflict_field}'.")

        return ProductEnrichment(
            product_id=product.product_id,
            manufacturer=product.manufacturer,
            model=product.model,
            summary=summary,
            technical_description=technical_description,
            key_selling_points=key_selling_points,
            target_applications=target_applications,
            suggested_keywords=suggested_keywords,
            inferred_fields=inferred_fields,
            source_backed_claims=source_backed_claims,
            inferred_claims=inferred_claims,
            unresolved_conflicts=unresolved_conflicts,
            missing_information_notes=missing_notes,
            enrichment_warnings=warnings,
            provider=self._client.provider,
            llm_model=self._client.model,
            prompt_version=PROMPT_VERSION,
        )


class BatchEnricher:
    """
    Batch processor executing AI enrichment across all 12 dataset products.
    """

    def __init__(self, data_dir: Path, enricher: Optional[MotorEnricher] = None):
        self.data_dir = data_dir
        self.processed_dir = data_dir / "processed"
        self.enricher = enricher or MotorEnricher()

    def run_all(self) -> BatchEnrichmentReport:
        """Run enrichment across all products with normalized + validation data."""
        manifest_path = self.data_dir / "dataset_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        product_ids = [entry["product_id"] for entry in manifest]

        report = BatchEnrichmentReport(
            provider=self.enricher.client.provider,
            model=self.enricher.client.model,
        )

        for pid in product_ids:
            p_dir = self.processed_dir / pid
            norm_file = p_dir / "normalized_product.json"
            val_file = p_dir / "validation_report.json"

            if not norm_file.exists() or not val_file.exists():
                logger.error("Missing inputs for %s (norm=%s, val=%s)", pid, norm_file.exists(), val_file.exists())
                report.products_processed += 1
                report.products_failed += 1
                continue

            try:
                # Load normalized product
                from productiq.validation.validator import _load_normalized_product
                norm_prod = _load_normalized_product(norm_file)

                # Load validation report
                val_data = json.loads(val_file.read_text(encoding="utf-8"))
                val_report = ProductValidationReport(
                    product_id=val_data["product_id"],
                    manufacturer=val_data["manufacturer"],
                    model=val_data["model"],
                    overall_status=ValidationStatus(val_data["overall_status"]),
                )
                from productiq.validation.models import ValidationFinding, ValidationSeverity, ValidationCategory
                for fd in val_data.get("findings", []):
                    val_report.findings.append(ValidationFinding(
                        rule_id=fd["rule_id"],
                        category=ValidationCategory(fd["category"]),
                        status=ValidationStatus(fd["status"]),
                        severity=ValidationSeverity(fd["severity"]),
                        field=fd["field"],
                        description=fd["description"],
                        explanation=fd.get("explanation", ""),
                    ))

                # Execute enrichment
                enrichment = self.enricher.enrich(norm_prod, val_report)

                # Save per-product output
                out_path = p_dir / "enrichment.json"
                out_path.write_text(enrichment.to_json(), encoding="utf-8")

                # Accumulate statistics
                report.products_processed += 1
                report.products_enriched += 1
                report.total_claims_generated += enrichment.total_claims
                report.source_backed_claims_count += len(enrichment.source_backed_claims)
                report.inferred_claims_count += len(enrichment.inferred_claims)
                report.unresolved_conflicts_count += len(enrichment.unresolved_conflicts)

            except Exception as exc:
                logger.error("Failed to enrich %s: %s", pid, exc, exc_info=True)
                report.products_processed += 1
                report.products_failed += 1

        # Save batch enrichment report
        batch_out = self.processed_dir / "batch_enrichment_report.json"
        batch_out.write_text(report.to_json(), encoding="utf-8")
        logger.info("Saved batch enrichment report to %s", batch_out)

        return report
