"""
ProductIQ Phase 3 — Batch Validation Runner
============================================
Runs the full validation pipeline over all 12 normalized products.

Usage:
    python scripts/run_validation.py

Output:
    data/processed/<product_id>/validation_report.json  (12 files)
    data/processed/batch_validation_report.json          (batch summary)
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from productiq.logging_setup import setup_logging
from productiq.validation import BatchValidator

setup_logging()
logger = logging.getLogger(__name__)


def main() -> int:
    data_dir = PROJECT_ROOT / "data"

    print("=" * 60)
    print("  ProductIQ Phase 3 — Batch Validation")
    print("=" * 60)
    print(f"  Data directory : {data_dir}")
    print(f"  Output         : data/processed/<product_id>/validation_report.json")
    print()

    batch = BatchValidator(data_dir=data_dir)

    try:
        report = batch.run_all()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    print()
    print("=" * 60)
    print("  Validation Summary")
    print("=" * 60)
    print(f"  Products processed    : {report.products_processed}")
    print(f"  Products passing      : {report.products_passing}")
    print(f"  Products with warnings: {report.products_with_warn}")
    print(f"  Products with conflict: {report.products_with_conflict}")
    print(f"  Products failing      : {report.products_failing}")
    print(f"  Total findings        : {report.total_findings}")
    print(f"    PASS                : {report.findings_pass}")
    print(f"    WARNING             : {report.findings_warning}")
    print(f"    CONFLICT            : {report.findings_conflict}")
    print(f"    FAIL                : {report.findings_fail}")
    print(f"    NOT_CHECKED         : {report.findings_not_checked}")
    print()
    print("  Findings by category:")
    for cat, count in sorted(report.findings_by_category.items()):
        print(f"    {cat:<20}: {count}")
    print()

    if report.products_failing > 0:
        print(f"[WARN] {report.products_failing} product(s) have FAIL-level findings.")
        return 1

    print(f"[OK] All {report.products_processed} products validated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
