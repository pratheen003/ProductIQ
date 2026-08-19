"""
ProductIQ Trust Service & Orchestrator — Phase 5
=================================================
Service layers for computing, serializing, and managing trust reports.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from productiq.normalization.models import (
    NormalizedProduct,
    NormalizedField,
    NormalizationOutcome,
    ConflictRecord,
    EvidenceRef,
)
from productiq.validation.models import (
    ProductValidationReport,
    ValidationFinding,
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
    FindingEvidenceRef,
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
    BatchTrustReport,
)
from productiq.trust.evaluator import MotorTrustEvaluator

logger = logging.getLogger("productiq.trust")


class ProductTrustAnalyzer:
    """
    Analyzes a single product by ingesting its Phase 2, Phase 3, and Phase 4 artifacts.
    """

    def __init__(self, evaluator: Optional[MotorTrustEvaluator] = None):
        self.evaluator = evaluator or MotorTrustEvaluator()

    def analyze(
        self,
        product_id: str,
        data_dir: Path | str,
        save_output: bool = True,
    ) -> ProductTrustReport:
        """
        Load processed artifacts for product_id and produce a ProductTrustReport.
        """
        data_path = Path(data_dir)
        product_dir = data_path / "processed" / product_id

        # 1. Load NormalizedProduct (Phase 2)
        norm_product = self._load_normalized_product(product_dir / "normalized_product.json")

        # 2. Load ValidationReport (Phase 3)
        val_report = self._load_validation_report(product_dir / "validation_report.json")

        # 3. Load ProductEnrichment (Phase 4)
        enrichment = self._load_enrichment(product_dir / "enrichment.json")

        # Extract manufacturer and model
        mfg = "WEG"
        mdl = "W22"
        if norm_product:
            mfg = norm_product.manufacturer or mfg
            mdl = norm_product.model or mdl
        elif val_report:
            mfg = val_report.manufacturer or mfg
            mdl = val_report.model or mdl
        elif enrichment:
            mfg = enrichment.manufacturer or mfg
            mdl = enrichment.model or mdl

        report = self.evaluator.evaluate(
            normalized_product=norm_product,
            validation_report=val_report,
            enrichment=enrichment,
            product_id=product_id,
            manufacturer=mfg,
            model=mdl,
        )

        if save_output and product_dir.exists():
            out_file = product_dir / "trust_report.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
            logger.info(f"Saved trust report to {out_file}")

        return report

    def _load_normalized_product(self, path: Path) -> Optional[NormalizedProduct]:
        if not path.exists():
            logger.debug(f"Normalized product not found at {path}")
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            fields: Dict[str, NormalizedField] = {}
            for fname, fdata in data.get("fields", {}).items():
                refs = [
                    EvidenceRef(
                        source_id=r.get("source_id", ""),
                        source_type=r.get("source_type", "pdf"),
                        product_id=r.get("product_id", ""),
                        attribute=r.get("attribute", fname),
                        raw_value=r.get("raw_value", ""),
                        raw_unit=r.get("raw_unit"),
                        parsed_value=r.get("parsed_value"),
                        method=r.get("method", "table"),
                        confidence=r.get("confidence", 1.0),
                        page=r.get("page"),
                        row=r.get("row"),
                        column=r.get("column"),
                        url=r.get("url"),
                        section=r.get("section"),
                    )
                    for r in fdata.get("evidence_refs", [])
                ]

                conflicts = []
                for c in fdata.get("conflicts", []):
                    src_a_data = c.get("source_a", {})
                    src_b_data = c.get("source_b", {})
                    src_a = EvidenceRef(
                        source_id=src_a_data.get("source_id", ""),
                        source_type=src_a_data.get("source_type", "pdf"),
                        product_id=src_a_data.get("product_id", ""),
                        attribute=src_a_data.get("attribute", fname),
                        raw_value=src_a_data.get("raw_value", ""),
                        raw_unit=src_a_data.get("raw_unit"),
                        parsed_value=src_a_data.get("parsed_value"),
                        method=src_a_data.get("method", "table"),
                        confidence=src_a_data.get("confidence", 1.0),
                        page=src_a_data.get("page"),
                        row=src_a_data.get("row"),
                        column=src_a_data.get("column"),
                    )
                    src_b = EvidenceRef(
                        source_id=src_b_data.get("source_id", ""),
                        source_type=src_b_data.get("source_type", "csv"),
                        product_id=src_b_data.get("product_id", ""),
                        attribute=src_b_data.get("attribute", fname),
                        raw_value=src_b_data.get("raw_value", ""),
                        raw_unit=src_b_data.get("raw_unit"),
                        parsed_value=src_b_data.get("parsed_value"),
                        method=src_b_data.get("method", "column"),
                        confidence=src_b_data.get("confidence", 1.0),
                        page=src_b_data.get("page"),
                        row=src_b_data.get("row"),
                        column=src_b_data.get("column"),
                    )
                    conflicts.append(ConflictRecord(
                        canonical_field=c.get("canonical_field", fname),
                        value_a=c.get("value_a"),
                        unit_a=c.get("unit_a"),
                        source_a=src_a,
                        value_b=c.get("value_b"),
                        unit_b=c.get("unit_b"),
                        source_b=src_b,
                        note=c.get("note", ""),
                    ))

                outcome_str = fdata.get("outcome", "missing")
                try:
                    outcome = NormalizationOutcome(outcome_str)
                except ValueError:
                    outcome = NormalizationOutcome.MISSING

                fields[fname] = NormalizedField(
                    canonical_field=fname,
                    canonical_unit=fdata.get("canonical_unit"),
                    canonical_value=fdata.get("canonical_value"),
                    outcome=outcome,
                    evidence_refs=refs,
                    conflicts=conflicts,
                )

            return NormalizedProduct(
                product_id=data.get("product_id", ""),
                manufacturer=data.get("manufacturer", "WEG"),
                model=data.get("model", "W22"),
                fields=fields,
            )
        except Exception as e:
            logger.warning(f"Error loading normalized product from {path}: {e}")
            return None

    def _load_validation_report(self, path: Path) -> Optional[ProductValidationReport]:
        if not path.exists():
            logger.debug(f"Validation report not found at {path}")
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            findings: List[ValidationFinding] = []
            for f in data.get("findings", []):
                refs = [
                    FindingEvidenceRef(
                        source_id=r.get("source_id", ""),
                        source_type=r.get("source_type", "pdf"),
                        attribute=r.get("attribute", ""),
                        raw_value=r.get("raw_value", ""),
                        raw_unit=r.get("raw_unit"),
                        page=r.get("page"),
                        row=r.get("row"),
                        column=r.get("column"),
                        section=r.get("section"),
                    )
                    for r in f.get("evidence_refs", [])
                ]

                cat = ValidationCategory.SCHEMA
                try:
                    cat = ValidationCategory(f.get("category", "SCHEMA"))
                except ValueError:
                    pass

                st = ValidationStatus.PASS
                try:
                    st = ValidationStatus(f.get("status", "PASS"))
                except ValueError:
                    pass

                sev = ValidationSeverity.INFO
                try:
                    sev = ValidationSeverity(f.get("severity", "INFO"))
                except ValueError:
                    pass

                findings.append(ValidationFinding(
                    rule_id=f.get("rule_id", ""),
                    category=cat,
                    status=st,
                    severity=sev,
                    field=f.get("field"),
                    description=f.get("description", ""),
                    actual_value=f.get("actual_value"),
                    actual_unit=f.get("actual_unit"),
                    expected_condition=f.get("expected_condition", ""),
                    explanation=f.get("explanation", ""),
                    evidence_refs=refs,
                ))

            overall_st = ValidationStatus.PASS
            try:
                overall_st = ValidationStatus(data.get("overall_status", "PASS"))
            except ValueError:
                pass

            return ProductValidationReport(
                product_id=data.get("product_id", ""),
                manufacturer=data.get("manufacturer", "WEG"),
                model=data.get("model", "W22"),
                findings=findings,
                overall_status=overall_st,
            )
        except Exception as e:
            logger.warning(f"Error loading validation report from {path}: {e}")
            return None

    def _load_enrichment(self, path: Path) -> Optional[ProductEnrichment]:
        if not path.exists():
            logger.debug(f"Enrichment report not found at {path}")
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProductEnrichment.from_dict(data)
        except Exception as e:
            logger.warning(f"Error loading enrichment report from {path}: {e}")
            return None


class BatchTrustAnalyzer:
    """
    Orchestrates trust analysis across all products in the dataset.
    """

    def __init__(self, analyzer: Optional[ProductTrustAnalyzer] = None):
        self.analyzer = analyzer or ProductTrustAnalyzer()

    def analyze_dataset(
        self,
        data_dir: Path | str,
        manifest_path: Optional[Path | str] = None,
        save_output: bool = True,
    ) -> BatchTrustReport:
        """
        Analyze all dataset products and generate a BatchTrustReport.
        """
        data_path = Path(data_dir)
        m_path = Path(manifest_path) if manifest_path else (data_path / "dataset_manifest.json")

        product_ids = []
        if m_path.exists():
            try:
                with open(m_path, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                    if isinstance(m_data, list):
                        product_ids = [p["product_id"] for p in m_data if "product_id" in p]
                    elif isinstance(m_data, dict):
                        product_ids = [p["product_id"] for p in m_data.get("products", [])]
            except Exception as e:
                logger.warning(f"Error reading manifest {m_path}: {e}")

        # Fallback: scan processed directory
        if not product_ids:
            proc_dir = data_path / "processed"
            if proc_dir.exists():
                product_ids = sorted([
                    d.name for d in proc_dir.iterdir()
                    if d.is_dir() and d.name.startswith("PIQ-")
                ])

        reports: List[ProductTrustReport] = []
        product_summaries: List[Dict[str, Any]] = []

        trusted_count = 0
        review_required_count = 0
        conflicted_count = 0
        publishable_count = 0
        publishable_with_warning_count = 0
        not_publishable_count = 0
        total_review_items = 0
        total_score = 0.0

        for pid in product_ids:
            logger.info(f"Analyzing trust for product {pid}...")
            report = self.analyzer.analyze(pid, data_path, save_output=save_output)
            reports.append(report)

            if report.overall_trust_status == TrustStatus.TRUSTED:
                trusted_count += 1
            elif report.overall_trust_status == TrustStatus.CONFLICTED:
                conflicted_count += 1
            elif report.overall_trust_status == TrustStatus.REVIEW_REQUIRED:
                review_required_count += 1

            if report.overall_publishability == PublishabilityStatus.PUBLISHABLE:
                publishable_count += 1
            elif report.overall_publishability == PublishabilityStatus.PUBLISHABLE_WITH_WARNING:
                publishable_with_warning_count += 1
            elif report.overall_publishability == PublishabilityStatus.NOT_PUBLISHABLE:
                not_publishable_count += 1

            total_review_items += len(report.review_queue)
            total_score += report.trust_score

            product_summaries.append({
                "product_id": report.product_id,
                "manufacturer": report.manufacturer,
                "model": report.model,
                "overall_trust_status": report.overall_trust_status.value,
                "overall_publishability": report.overall_publishability.value,
                "trust_score": report.trust_score,
                "review_items_count": len(report.review_queue),
                "conflicts_count": len(report.unresolved_conflicts),
                "publishable_attributes_count": len(report.publishable_attributes),
                "restricted_attributes_count": len(report.restricted_attributes),
            })

        avg_score = (total_score / len(reports)) if reports else 0.0

        batch_report = BatchTrustReport(
            total_products=len(reports),
            trusted_count=trusted_count,
            review_required_count=review_required_count,
            conflicted_count=conflicted_count,
            publishable_count=publishable_count,
            publishable_with_warning_count=publishable_with_warning_count,
            not_publishable_count=not_publishable_count,
            avg_trust_score=avg_score,
            total_review_items=total_review_items,
            products=product_summaries,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        if save_output:
            out_file = data_path / "processed" / "batch_trust_report.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(batch_report.to_dict(), f, indent=2)
            logger.info(f"Saved batch trust report to {out_file}")

        return batch_report
