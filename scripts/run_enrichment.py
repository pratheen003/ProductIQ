"""
ProductIQ Phase 4 — Batch AI Enrichment Runner
===============================================
Runs the AI enrichment pipeline over all 12 normalized & validated products.

Usage:
    python scripts/run_enrichment.py

Output:
    data/processed/<product_id>/enrichment.json  (12 files)
    data/processed/batch_enrichment_report.json  (batch summary)
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from productiq.logging_setup import setup_logging
from productiq.config import load_config
from productiq.enrichment import BatchEnricher

setup_logging()
logger = logging.getLogger(__name__)


def main() -> int:
    config = load_config()
    data_dir = PROJECT_ROOT / "data"

    print("=" * 60)
    print("  ProductIQ Phase 4 — AI Enrichment")
    print("=" * 60)
    print(f"  Data directory : {data_dir}")
    print(f"  LLM Provider   : {config.llm_provider}")
    print(f"  LLM Model      : {config.llm_model}")
    print(f"  Output         : data/processed/<product_id>/enrichment.json")
    print()

    if not config.has_llm_key:
        print(f"[ERROR] No API key configured for provider '{config.llm_provider}'.")
        print("Set GROQ_API_KEY or LLM_API_KEY in .env before running enrichment.")
        return 1

    enricher = BatchEnricher(data_dir=data_dir)

    try:
        report = enricher.run_all()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    print()
    print("=" * 60)
    print("  Enrichment Summary")
    print("=" * 60)
    print(f"  Products processed         : {report.products_processed}")
    print(f"  Products enriched          : {report.products_enriched}")
    print(f"  Products failed            : {report.products_failed}")
    print(f"  Total claims generated     : {report.total_claims_generated}")
    print(f"    Source-backed claims     : {report.source_backed_claims_count}")
    print(f"    Inferred claims          : {report.inferred_claims_count}")
    print(f"  Unresolved conflicts saved : {report.unresolved_conflicts_count}")
    print(f"  Provider / Model           : {report.provider} ({report.model})")
    print()

    if report.products_failed > 0:
        print(f"[WARN] {report.products_failed} product(s) failed enrichment.")
        return 1

    print(f"[OK] All {report.products_enriched} products enriched successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
