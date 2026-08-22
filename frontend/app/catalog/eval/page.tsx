"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  Clock,
  CheckCircle2,
  RefreshCw,
  Layers,
  ArrowLeft,
  FileCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { CatalogComplianceEvalDTO } from "@/lib/types";

export default function CatalogComplianceEvalPage() {
  const [data, setData] = useState<CatalogComplianceEvalDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (forceRefresh = false) => {
    if (forceRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const res = await api.getCatalogComplianceEval();
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load compliance evaluation");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-brand-accent animate-spin" />
          <p className="text-sm text-slate-500 font-medium">Computing 1,000-row compliance metrics...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8">
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-rose-700">
          <h3 className="font-semibold text-lg mb-2">Error Loading Compliance Metrics</h3>
          <p className="text-sm mb-4">{error || "Could not retrieve compliance evaluation."}</p>
          <button
            onClick={() => loadData(true)}
            className="px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-medium hover:bg-rose-700 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const mDist = data.manufacturer_status_distribution;
  const bDist = data.brand_status_distribution;
  const oDist = data.overall_status_distribution;

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 text-xs font-bold font-mono uppercase bg-blue-100 text-blue-800 rounded">
              Mechanism B Evaluation
            </span>
            <span className="text-xs font-mono text-slate-500">n=1,000 Input Rows</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Rule-Compliance &amp; Vocabulary Evaluation
          </h1>
          <p className="text-slate-600 mt-1">
            Measures internal consistency, active conflict detection, and vocabulary integrity at scale without unseen ground truth.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            <span>{refreshing ? "Re-evaluating..." : "Recompute 1k Batch"}</span>
          </button>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase">Approved Vocabulary</span>
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="text-3xl font-bold text-slate-900 font-mono mb-1">{data.lov_compliance_rate_pct}%</div>
          <p className="text-xs text-emerald-700 font-medium">0% invented values</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase">Conflict Detection Rate</span>
            <AlertTriangle className="w-5 h-5 text-amber-600" />
          </div>
          <div className="text-3xl font-bold text-amber-900 font-mono mb-1">{data.conflict_detection_rate_pct}%</div>
          <p className="text-xs text-amber-700 font-medium">{data.total_conflicts_detected} disagreeing rows flagged</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase">Placeholder Filtering</span>
            <FileCheck className="w-5 h-5 text-blue-600" />
          </div>
          <div className="text-3xl font-bold text-slate-900 font-mono mb-1">{data.placeholder_filtering_rate_pct}%</div>
          <p className="text-xs text-blue-700 font-medium">{data.rows_with_placeholders_filtered} rows cleansed</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase">Throughput</span>
            <Clock className="w-5 h-5 text-indigo-600" />
          </div>
          <div className="text-3xl font-bold text-slate-900 font-mono mb-1">{data.throughput_rows_per_second.toLocaleString()} /s</div>
          <p className="text-xs text-slate-500 font-medium">{data.total_duration_ms.toFixed(1)} ms total latency</p>
        </div>
      </div>

      {/* Multi-Dimensional Status Distribution Table */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="font-bold text-slate-900 text-base">
              4-Tier Trust Status Distribution Across 1,000 Rows
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Breakdown across Manufacturer, Brand, and Overall Product Trust classifications.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Entity Dimension</th>
                <th className="py-3 px-4 text-emerald-700">Verified</th>
                <th className="py-3 px-4 text-blue-700">Inferred</th>
                <th className="py-3 px-4 text-amber-700">Conflicted</th>
                <th className="py-3 px-4 text-slate-600">Unknown (Safe Suppression)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr className="hover:bg-slate-50/60">
                <td className="py-3 px-4 font-bold text-slate-900">Manufacturer Name</td>
                <td className="py-3 px-4 font-mono">{mDist.verified_count} ({mDist.verified_pct}%)</td>
                <td className="py-3 px-4 font-mono">{mDist.inferred_count} ({mDist.inferred_pct}%)</td>
                <td className="py-3 px-4 font-mono font-bold text-amber-800">{mDist.conflicted_count} ({mDist.conflicted_pct}%)</td>
                <td className="py-3 px-4 font-mono text-slate-600">{mDist.unknown_count} ({mDist.unknown_pct}%)</td>
              </tr>
              <tr className="hover:bg-slate-50/60">
                <td className="py-3 px-4 font-bold text-slate-900">Brand Name</td>
                <td className="py-3 px-4 font-mono">{bDist.verified_count} ({bDist.verified_pct}%)</td>
                <td className="py-3 px-4 font-mono">{bDist.inferred_count} ({bDist.inferred_pct}%)</td>
                <td className="py-3 px-4 font-mono font-bold text-amber-800">{bDist.conflicted_count} ({bDist.conflicted_pct}%)</td>
                <td className="py-3 px-4 font-mono text-slate-600">{bDist.unknown_count} ({bDist.unknown_pct}%)</td>
              </tr>
              <tr className="hover:bg-slate-50/60 bg-slate-50/40">
                <td className="py-3 px-4 font-bold text-slate-900">Overall Product Trust</td>
                <td className="py-3 px-4 font-mono font-bold text-emerald-700">{oDist.verified_count} ({oDist.verified_pct}%)</td>
                <td className="py-3 px-4 font-mono font-bold text-blue-700">{oDist.inferred_count} ({oDist.inferred_pct}%)</td>
                <td className="py-3 px-4 font-mono font-bold text-amber-800">{oDist.conflicted_count} ({oDist.conflicted_pct}%)</td>
                <td className="py-3 px-4 font-mono font-bold text-slate-700">{oDist.unknown_count} ({oDist.unknown_pct}%)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Discovered Cross-Column Conflict Inspector */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div>
          <h3 className="font-bold text-slate-900 text-base">
            Sample Detected Cross-Column Brand Conflicts (Total: {data.total_conflicts_detected})
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Examples where input distributor columns asserted contradictory brand identities.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.conflict_examples.map((ex) => (
            <div key={ex.row_id} className="p-4 bg-amber-50/50 rounded-xl border border-amber-200 space-y-2 text-xs">
              <div className="flex justify-between items-center">
                <span className="font-mono font-bold text-slate-900">Row #{ex.row_id} ({ex.mfg_part_num})</span>
                <span className="px-2 py-0.5 bg-amber-100 text-amber-800 font-bold rounded">
                  Conflicted
                </span>
              </div>
              <p className="text-slate-700 truncate" title={ex.part_desc || ""}>
                {ex.part_desc || "No description"}
              </p>
              <div className="p-2 bg-white rounded border border-amber-100 text-[11px] text-amber-900 font-mono">
                {ex.reason}
              </div>
              <div className="flex justify-end">
                <Link
                  href={`/catalog/products/${ex.row_id}`}
                  className="text-brand-accent font-semibold hover:underline"
                >
                  Inspect Conflict Detail →
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
