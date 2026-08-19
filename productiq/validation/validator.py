"""
ProductIQ Motor Validator — Phase 3
=====================================
Main orchestrator: loads Phase 2 NormalizedProduct → applies validation rules
→ produces ProductValidationReport.

Pipeline per product:
  1. Load normalized_product.json from data/processed/<product_id>/
  2. Reconstruct NormalizedProduct from JSON
  3. Apply all validation rules in sequence
  4. Compute overall status from worst finding
  5. Write validation_report.json alongside normalized_product.json

Design commitments:
  - No LLM calls. All validation is deterministic rule-based logic.
  - No fabricated values. Validation only reads, never invents.
  - Conflicts are surfaced, never resolved.
  - Phase 2 provenance is fully preserved.
  - Malformed normalized products → ValidationFinding(FAIL), not crash.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from productiq.normalization.models import (
    NormalizedProduct,
    NormalizedField,
    NormalizationOutcome,
    EvidenceRef,
    ConflictRecord,
)
from productiq.validation.models import (
    BatchValidationReport,
    ProductValidationReport,
    ValidationFinding,
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
)
from productiq.validation.rules import (
    check_schema_canonical_units,
    check_schema_normalization_version,
    check_required_fields,
    check_important_fields,
    check_missing_data_inventory,
    check_range_rated_power,
    check_range_rated_voltage,
    check_range_rated_current,
    check_range_rated_speed,
    check_range_efficiency,
    check_range_power_factor,
    check_range_weight,
    check_cross_source_consistency,
    check_engineering_torque_power_rpm,
    check_engineering_efficiency_plausibility,
    check_engineering_synchronous_speed,
    check_known_current_conflict,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NormalizedProduct loader from saved JSON
# ---------------------------------------------------------------------------

def _load_normalized_product(path: Path) -> NormalizedProduct:
    """Load and reconstruct a NormalizedProduct from its JSON file."""
    raw = json.loads(path.read_text(encoding="utf-8"))

    # Reconstruct fields
    fields: Dict[str, NormalizedField] = {}
    for field_name, fd in raw.get("fields", {}).items():
        fields[field_name] = NormalizedField.from_dict(fd)

    # Reconstruct unmapped evidence
    unmapped: List[EvidenceRef] = []
    for ev in raw.get("unmapped_evidence", []):
        unmapped.append(EvidenceRef(**ev))

    return NormalizedProduct(
        product_id=raw["product_id"],
        manufacturer=raw["manufacturer"],
        model=raw["model"],
        product_type=raw.get("product_type", "three_phase_induction_motor"),
        fields=fields,
        unmapped_evidence=unmapped,
        normalization_version=raw.get("normalization_version", "2.0.0"),
        normalization_notes=raw.get("normalization_notes", []),
    )


# ---------------------------------------------------------------------------
# Motor Validator — validates one NormalizedProduct
# ---------------------------------------------------------------------------

class MotorValidator:
    """
    Applies all Phase 3 validation rules to a single NormalizedProduct.

    Rules are applied in order:
      A. Schema validation
      B. Required-field validation
      D. Range/plausibility validation
      F. Cross-source consistency (conflict detection)
      G. Engineering plausibility
      H. Missing data inventory
      I. Known specific conflicts
    """

    def validate(self, product: NormalizedProduct) -> ProductValidationReport:
        """Run all validation rules and return a ProductValidationReport."""
        findings: List[ValidationFinding] = []

        # A. Schema validation
        findings.extend(check_schema_canonical_units(product))
        findings.extend(check_schema_normalization_version(product))

        # B. Required-field and important-field validation
        findings.extend(check_required_fields(product))
        findings.extend(check_important_fields(product))

        # D. Range / plausibility
        findings.extend(check_range_rated_power(product))
        findings.extend(check_range_rated_voltage(product))
        findings.extend(check_range_rated_current(product))
        findings.extend(check_range_rated_speed(product))
        findings.extend(check_range_efficiency(product))
        findings.extend(check_range_power_factor(product))
        findings.extend(check_range_weight(product))

        # F. Cross-source consistency (all conflicted fields)
        findings.extend(check_cross_source_consistency(product))

        # G. Engineering plausibility
        findings.extend(check_engineering_torque_power_rpm(product))
        findings.extend(check_engineering_efficiency_plausibility(product))
        findings.extend(check_engineering_synchronous_speed(product))

        # H. Missing data inventory
        findings.extend(check_missing_data_inventory(product))

        # I. Specific known conflicts
        findings.extend(check_known_current_conflict(product))

        # Assemble report
        report = ProductValidationReport(
            product_id=product.product_id,
            manufacturer=product.manufacturer,
            model=product.model,
            findings=findings,
        )
        report.overall_status = report.compute_overall_status()

        logger.info(
            "Validated %s: %d findings "
            "(%d pass, %d warn, %d conflict, %d fail, %d not-checked) | overall=%s",
            product.product_id,
            report.total_findings,
            report.pass_count,
            report.warning_count,
            report.conflict_count,
            report.fail_count,
            report.not_checked_count,
            report.overall_status.value,
        )
        return report


# ---------------------------------------------------------------------------
# Batch Validator — validates all 12 products
# ---------------------------------------------------------------------------

class BatchValidator:
    """
    Loads and validates all NormalizedProduct files found in data/processed/.
    Writes validation_report.json to each product directory.
    Writes batch_validation_report.json to data/processed/.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.processed_dir = data_dir / "processed"
        self.validator = MotorValidator()

    def _find_product_dirs(self) -> List[Path]:
        """Return all product directories that have a normalized_product.json."""
        dirs = []
        for d in sorted(self.processed_dir.iterdir()):
            if d.is_dir() and (d / "normalized_product.json").exists():
                dirs.append(d)
        return dirs

    def run_all(self) -> BatchValidationReport:
        """Validate all products and return a BatchValidationReport."""
        manifest_path = self.data_dir / "dataset_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        product_ids = [entry["product_id"] for entry in manifest]

        batch = BatchValidationReport()

        for pid in product_ids:
            product_dir = self.processed_dir / pid
            norm_path = product_dir / "normalized_product.json"

            if not norm_path.exists():
                logger.error("normalized_product.json missing for %s", pid)
                batch.products_processed += 1
                batch.products_failing += 1
                continue

            try:
                product = _load_normalized_product(norm_path)
                report = self.validator.validate(product)

                # Save per-product validation report
                out_path = product_dir / "validation_report.json"
                out_path.write_text(report.to_json(), encoding="utf-8")
                logger.info("Saved validation report: %s", out_path)

                # Accumulate batch stats
                batch.products_processed += 1
                if report.overall_status == ValidationStatus.PASS:
                    batch.products_passing += 1
                elif report.overall_status == ValidationStatus.WARNING:
                    batch.products_with_warn += 1
                elif report.overall_status == ValidationStatus.CONFLICT:
                    batch.products_with_conflict += 1
                elif report.overall_status == ValidationStatus.FAIL:
                    batch.products_failing += 1

                batch.total_findings += report.total_findings
                batch.findings_pass += report.pass_count
                batch.findings_warning += report.warning_count
                batch.findings_conflict += report.conflict_count
                batch.findings_fail += report.fail_count
                batch.findings_not_checked += report.not_checked_count

                for cat, count in report.findings_by_category.items():
                    batch.findings_by_category[cat] = (
                        batch.findings_by_category.get(cat, 0) + count
                    )

            except Exception as exc:
                logger.error("Failed to validate %s: %s", pid, exc, exc_info=True)
                batch.products_processed += 1
                batch.products_failing += 1

        # Save batch report
        report_path = self.processed_dir / "batch_validation_report.json"
        report_path.write_text(batch.to_json(), encoding="utf-8")
        logger.info("Saved batch validation report: %s", report_path)

        return batch
