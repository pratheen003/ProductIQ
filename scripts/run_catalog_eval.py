"""
ProductIQ Catalog Dual-Mechanism Evaluation Runner
===================================================
Executes Mechanism A (Exact-Match on n=2 gold standard rows) and
Mechanism B (Rule-Compliance at Scale across all 1,000 input rows).
"""
import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from productiq_catalog.scoring.exact_match_eval import ExactMatchEvaluator
from productiq_catalog.scoring.compliance_metrics import ComplianceEvaluator


def main():
    print("=" * 70)
    print("  ProductIQ Catalog Dual-Mechanism Evaluation (Unilog Pipeline)")
    print("=" * 70)

    # 1. Mechanism A: Exact-Match Validation (n=2)
    print("\n--- MECHANISM A: EXACT-MATCH GOLD STANDARD VALIDATION (n=2) ---")
    exact_eval = ExactMatchEvaluator()
    summary_a = exact_eval.evaluate()

    print(f"Sample Size: {summary_a.sample_size_label}")
    print(f"Overall Match Rate: {summary_a.overall_exact_match_rate_pct}% ({summary_a.total_fields_matched}/{summary_a.total_fields_compared} fields)")
    print(f"Summary Statement: {summary_a.summary_statement}\n")

    for row in summary_a.rows:
        print(f"  Row {row.row_id} (Part#: {row.mfg_part_num}): Accuracy = {row.row_accuracy_pct}% ({row.fields_matched}/{row.fields_compared} fields)")
        for c in row.field_comparisons:
            mark = "[MATCH]" if c.is_exact_match else "[DIFF]"
            print(f"    {mark} {c.field_name:25s} -> Pipeline: {repr(c.pipeline_value):30s} | Expected: {repr(c.expected_value)} ({c.status_tier})")

    # 2. Mechanism B: Rule-Compliance & Vocabulary Metrics (1,000 items)
    print("\n" + "=" * 70)
    print("--- MECHANISM B: RULE-COMPLIANCE & VOCABULARY METRICS AT SCALE (n=1,000) ---")
    comp_eval = ComplianceEvaluator()
    summary_b = comp_eval.evaluate(force_refresh=True)

    print(f"Total Input Rows Evaluated: {summary_b.total_input_rows}")
    print(f"LOV/Lookup Compliance Rate: {summary_b.lov_compliance_rate_pct}% (0% invented values)")
    print(f"Conflict Detection Rate:    {summary_b.conflict_detection_rate_pct}% ({summary_b.total_conflicts_detected} conflicts detected)")
    print(f"Placeholder Filtering Rate: {summary_b.placeholder_filtering_rate_pct}% ({summary_b.rows_with_placeholders_filtered} rows filtered)")
    print(f"Execution Throughput:       {summary_b.throughput_rows_per_second} rows/sec ({summary_b.total_duration_ms} ms total)")

    print("\nStatus Distributions Across 1,000 Rows:")
    print("  Manufacturer Status:")
    m = summary_b.manufacturer_status_distribution
    print(f"    Verified: {m.verified_count:4d} ({m.verified_pct:5.1f}%) | Inferred: {m.inferred_count:4d} ({m.inferred_pct:5.1f}%) | Conflicted: {m.conflicted_count:4d} ({m.conflicted_pct:5.1f}%) | Unknown: {m.unknown_count:4d} ({m.unknown_pct:5.1f}%)")

    print("  Brand Status:")
    b = summary_b.brand_status_distribution
    print(f"    Verified: {b.verified_count:4d} ({b.verified_pct:5.1f}%) | Inferred: {b.inferred_count:4d} ({b.inferred_pct:5.1f}%) | Conflicted: {b.conflicted_count:4d} ({b.conflicted_pct:5.1f}%) | Unknown: {b.unknown_count:4d} ({b.unknown_pct:5.1f}%)")

    print("  Overall Trust Status:")
    o = summary_b.overall_status_distribution
    print(f"    Verified: {o.verified_count:4d} ({o.verified_pct:5.1f}%) | Inferred: {o.inferred_count:4d} ({o.inferred_pct:5.1f}%) | Conflicted: {o.conflicted_count:4d} ({o.conflicted_pct:5.1f}%) | Unknown: {o.unknown_count:4d} ({o.unknown_pct:5.1f}%)")

    print("\n" + "=" * 70)
    print("  EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
