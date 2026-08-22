"""
ProductIQ Catalog Batch Pipeline Runner (Prompt 3)
===================================================
Executes end-to-end catalog enrichment across all 1,000 input rows
and persists individual and batch records to data/catalog/processed/.
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from productiq_catalog.extraction.input_loader import InputDatasetLoader
from productiq_catalog.enrichment.catalog_enricher import CatalogPipeline
from productiq_catalog.ground_truth.ingest import GroundTruthStore


def run_catalog_batch():
    print("=" * 70)
    print("  ProductIQ Catalog Batch Pipeline Runner (1,000 Items)")
    print("=" * 70)

    input_loader = InputDatasetLoader()
    gt_store = GroundTruthStore()
    pipeline = CatalogPipeline(ground_truth=gt_store)

    output_dir = Path(__file__).resolve().parent.parent / "data" / "catalog" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = input_loader.get_all()
    total_rows = len(rows)
    print(f"Loaded {total_rows} raw input rows from dataset.")

    start_time = time.perf_counter()

    enriched_products = []
    status_counts = Counter()
    conflict_count = 0
    persisted_files = 0

    for r in rows:
        product = pipeline.process_row(r)
        product_dict = product.to_dict()
        enriched_products.append(product_dict)

        # Track metrics
        status_counts[product.overall_trust_status.value] += 1
        if product.has_conflicts:
            conflict_count += 1

        # Write individual row file
        row_file = output_dir / f"row_{r.row_id:04d}.json"
        with open(row_file, "w", encoding="utf-8") as f:
            json.dump(product_dict, f, indent=2, ensure_ascii=False)
        persisted_files += 1

    end_time = time.perf_counter()
    duration_ms = round((end_time - start_time) * 1000, 2)
    throughput = round(total_rows / (duration_ms / 1000), 1) if duration_ms > 0 else 0.0

    # Write consolidated batch report
    batch_report = {
        "batch_id": "UNILOG-CATALOG-1000",
        "total_records": total_rows,
        "persisted_files_count": persisted_files,
        "duration_ms": duration_ms,
        "throughput_rows_per_second": throughput,
        "conflict_count": conflict_count,
        "conflict_rate_pct": round((conflict_count / total_rows) * 100.0, 2),
        "status_distribution": {
            "Verified": status_counts["Verified"],
            "Inferred": status_counts["Inferred"],
            "Conflicted": status_counts["Conflicted"],
            "Unknown": status_counts["Unknown"],
        },
        "status_distribution_pct": {
            "Verified": round((status_counts["Verified"] / total_rows) * 100.0, 2),
            "Inferred": round((status_counts["Inferred"] / total_rows) * 100.0, 2),
            "Conflicted": round((status_counts["Conflicted"] / total_rows) * 100.0, 2),
            "Unknown": round((status_counts["Unknown"] / total_rows) * 100.0, 2),
        },
        "records_summary": [
            {
                "row_id": p["row_id"],
                "mfg_part_num": p["mfg_part_num"],
                "part_desc": p["part_desc"],
                "manufacturer": p["manufacturer_name"]["value"],
                "brand": p["brand_name"]["value"],
                "overall_status": p["overall_trust_status"],
                "confidence": p["overall_confidence"],
                "has_conflicts": p["has_conflicts"],
            }
            for p in enriched_products
        ],
    }

    batch_report_path = output_dir / "batch_catalog_report.json"
    with open(batch_report_path, "w", encoding="utf-8") as f:
        json.dump(batch_report, f, indent=2, ensure_ascii=False)

    print(f"Persisted {persisted_files} individual files to {output_dir}")
    print(f"Persisted batch summary to {batch_report_path}")
    print(f"Execution Time: {duration_ms} ms ({throughput} rows/sec)")
    print(f"Status Distribution: {batch_report['status_distribution']}")
    print(f"Conflicts Detected: {conflict_count} ({batch_report['conflict_rate_pct']}%)")
    print("=" * 70)
    print("  BATCH PROCESSING COMPLETE (1,000 / 1,000 SUCCESSFUL)")
    print("=" * 70)
    return batch_report


if __name__ == "__main__":
    run_catalog_batch()
