#!/usr/bin/env python3
"""
ProductIQ Phase 5 — Trust Evaluation CLI Runner
================================================
Executes deterministic trust-aware intelligence analysis across all 12 motor products.
Consumes:
  - data/processed/<product_id>/normalized_product.json (Phase 2)
  - data/processed/<product_id>/validation_report.json (Phase 3)
  - data/processed/<product_id>/enrichment.json (Phase 4)
Produces:
  - data/processed/<product_id>/trust_report.json
  - data/processed/batch_trust_report.json
"""
import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from productiq.logging_setup import setup_logging
from productiq.config import load_config
from productiq.trust import BatchTrustAnalyzer


def main():
    parser = argparse.ArgumentParser(description="Run ProductIQ Phase 5 Trust Evaluation Batch Runner")
    parser.add_argument("--data-dir", type=str, default=None, help="Path to data directory")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.log_level)

    data_dir = Path(args.data_dir) if args.data_dir else Path(config.data_dir)

    print("=" * 60)
    print("  ProductIQ Phase 5 — Trust Evaluation Runner")
    print("=" * 60)
    print(f"  Data directory : {data_dir}")
    print("  Mode           : Deterministic / Zero-LLM (cost-free)")
    print("  Output         : data/processed/<product_id>/trust_report.json")
    print()

    analyzer = BatchTrustAnalyzer()
    batch_report = analyzer.analyze_dataset(data_dir=data_dir, save_output=True)

    print()
    print("=" * 60)
    print("  Trust Evaluation Summary")
    print("=" * 60)
    print(f"  Total products evaluated     : {batch_report.total_products}")
    print(f"  Trusted products             : {batch_report.trusted_count}")
    print(f"  Conflicted products          : {batch_report.conflicted_count}")
    print(f"  Review required products     : {batch_report.review_required_count}")
    print(f"  Average trust score          : {batch_report.avg_trust_score:.4f}")
    print(f"  Total review items generated : {batch_report.total_review_items}")
    print()

    for p in batch_report.products:
        print(
            f"  [{p['overall_trust_status']:<15}] {p['product_id']:<20} | "
            f"Score: {p['trust_score']:.4f} | "
            f"Publishability: {p['overall_publishability']:<24} | "
            f"Reviews: {p['review_items_count']:<2} | "
            f"Conflicts: {p['conflicts_count']}"
        )

    print()
    print("[OK] Trust evaluation completed successfully.")


if __name__ == "__main__":
    main()
