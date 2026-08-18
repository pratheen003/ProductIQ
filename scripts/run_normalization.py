"""
ProductIQ Phase 2 — Batch Normalization Runner
===============================================
Runs the full normalization pipeline over all 12 products in the dataset.

Usage:
    python scripts/run_normalization.py

Output:
    data/processed/<product_id>/normalized_product.json  (12 files)
    data/processed/normalization_report.json             (batch summary)
"""
import logging
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH when run directly
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from productiq.logging_setup import setup_logging
from productiq.normalization import BatchNormalizer

setup_logging()
logger = logging.getLogger(__name__)


def main() -> int:
    """Run batch normalization and return exit code."""
    data_dir = PROJECT_ROOT / "data"

    print("=" * 60)
    print("  ProductIQ Phase 2 — Batch Normalization")
    print("=" * 60)
    print(f"  Data directory : {data_dir}")
    print(f"  Output         : data/processed/<product_id>/normalized_product.json")
    print()

    batch = BatchNormalizer(data_dir=data_dir)

    try:
        report = batch.run_all()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    print()
    print("=" * 60)
    print("  Normalization Summary")
    print("=" * 60)
    print(f"  Products processed : {report.products_processed}")
    print(f"  Products succeeded : {report.products_succeeded}")
    print(f"  Products failed    : {report.products_failed}")
    print(f"  Evidence consumed  : {report.evidence_consumed}")
    print(f"  Fields normalized  : {report.fields_normalized}")
    print(f"  Fields conflicted  : {report.fields_conflicted}")
    print(f"  Fields missing     : {report.fields_missing}")
    print(f"  Unmapped attrs     : {report.unmapped_attrs}")
    print(f"  Parse errors       : {report.parse_errors}")
    print(f"  Unknown units      : {report.unknown_units}")
    print()

    if report.products_failed > 0:
        print(f"[WARN] {report.products_failed} product(s) failed normalization.")
        return 1

    print(f"[OK] All {report.products_succeeded} products normalized successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
