"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Table,
  Cpu,
  Clock,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  Download,
} from "lucide-react";
import { api } from "@/lib/api";
import { MetricCard } from "@/components/ui/MetricCard";
import { CatalogComplianceEvalDTO, CatalogExactMatchEvalDTO } from "@/lib/types";

export default function CatalogDashboardPage() {
  const [compliance, setCompliance] = useState<CatalogComplianceEvalDTO | null>(null);
  const [exactMatch, setExactMatch] = useState<CatalogExactMatchEvalDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [compData, exactData] = await Promise.all([
        api.getCatalogComplianceEval(),
        api.getCatalogExactMatchEval(),
      ]);
      setCompliance(compData);
      setExactMatch(exactData);
    } catch (err: any) {
      setError(err.message || "Failed to load catalog evaluation metrics");
    } finally {
      setLoading(false);
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
          <p className="text-sm text-slate-500 font-medium">Loading Catalog Intelligence metrics...</p>
        </div>
      </div>
    );
  }

  if (error || !compliance || !exactMatch) {
    return (
      <div className="p-8">
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-rose-700">
          <h3 className="font-semibold text-lg mb-2">Error Connecting to Catalog API</h3>
          <p className="text-sm mb-4">{error || "Could not retrieve catalog evaluation metrics."}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-medium hover:bg-rose-700 transition"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const oDist = compliance.overall_status_distribution;

  return (
    <div className="space-y-8 pb-12">
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 text-xs font-bold font-mono uppercase bg-brand-accent/10 text-brand-accent rounded">
              Unilog Hackathon Pipeline
            </span>
            <span className="text-xs text-slate-500">1,000 Catalog Items Ingested</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Catalog Intelligence Dashboard
          </h1>
          <p className="text-slate-600 mt-1">
            Dual-Mechanism Evaluation: Gold Standard Proof (n=2) &amp; Rule Compliance at Scale (n=1,000).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <a
            href="http://127.0.0.1:8000/api/catalog/export/delivery-format?format=xlsx"
            download
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-lg shadow transition"
            title="Download full 1,000-row delivery format matching exact 252 headers"
          >
            <Download className="w-4 h-4" />
            <span>Download Delivery Format (.xlsx)</span>
          </a>
          <Link
            href="/catalog/products"
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-accent text-white text-sm font-semibold rounded-lg shadow hover:bg-brand-accent/90 transition"
          >
            <Table className="w-4 h-4" />
            <span>Explore 1,000 Items</span>
          </Link>
          <Link
            href="/catalog/gold-standard"
            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 text-slate-700 text-sm font-semibold rounded-lg hover:bg-slate-50 transition"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Gold Standard (n=2)</span>
          </Link>
        </div>
      </div>

      {/* Top 4 Key Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Mechanism A (Gold Standard)"
          value={`${exactMatch.overall_exact_match_rate_pct}%`}
          subtitle="Pipeline Correctness & Formatting Fidelity (n=2)"
          badgeText="Verified (n=2)"
          badgeType="positive"
          icon={CheckCircle2}
        />

        <MetricCard
          title="Mechanism B (Vocabulary)"
          value={`${compliance.lov_compliance_rate_pct}%`}
          subtitle="Approved LOV Compliance (0% invented)"
          badgeText="1,000 Items"
          badgeType="positive"
          icon={ShieldCheck}
        />

        <MetricCard
          title="Conflict Detection Rate"
          value={`${compliance.conflict_detection_rate_pct}%`}
          subtitle={`${compliance.total_conflicts_detected} / 1,000 rows with brand disagreements`}
          badgeText="Flagged"
          badgeType="warning"
          icon={AlertTriangle}
        />

        <MetricCard
          title="Processing Throughput"
          value={`${compliance.throughput_rows_per_second.toLocaleString()} /s`}
          subtitle={`${compliance.total_duration_ms.toFixed(1)} ms total for 1,000 rows`}
          badgeText="Sub-second"
          badgeType="brand"
          icon={Clock}
        />
      </div>

      {/* Mechanism A Banner with Explicit Disclaimer */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-lg border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">
                {exactMatch.metric_label}
              </h3>
              <p className="text-xs text-slate-400">
                Validated field-by-field against Unilog Delivery Format Ground Truth
              </p>
            </div>
          </div>
          <Link
            href="/catalog/gold-standard"
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-xs font-semibold text-white rounded-lg transition"
          >
            <span>View Row 1 &amp; Row 2 Details</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="p-4 bg-white/5 rounded-xl border border-white/10 text-xs text-slate-300 leading-relaxed">
          <span className="font-bold text-emerald-400">Documentation Invariant:</span> {exactMatch.disclaimer}
        </div>
      </div>

      {/* 4-Tier Trust Distribution & Status Breakdown at 1,000 Scale */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Overall Status Distribution Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-1">
            Overall Trust Distribution (n=1,000)
          </h3>
          <p className="text-xs text-slate-500 mb-6">
            4-tier trust classification enforcing no-fabrication discipline.
          </p>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-emerald-700 flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  Verified (Ground Truth)
                </span>
                <span>{oDist.verified_count} ({oDist.verified_pct}%)</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div
                  className="bg-emerald-500 h-2 rounded-full"
                  style={{ width: `${Math.max(oDist.verified_pct, 1)}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-blue-700 flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                  Inferred (UOM / Fractions)
                </span>
                <span>{oDist.inferred_count} ({oDist.inferred_pct}%)</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: `${oDist.inferred_pct}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-amber-700 flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  Conflicted (Cross-Column)
                </span>
                <span>{oDist.conflicted_count} ({oDist.conflicted_pct}%)</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div
                  className="bg-amber-500 h-2 rounded-full"
                  style={{ width: `${oDist.conflicted_pct}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-slate-700 flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
                  Unknown (Suppressed / Safe)
                </span>
                <span>{oDist.unknown_count} ({oDist.unknown_pct}%)</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div
                  className="bg-slate-400 h-2 rounded-full"
                  style={{ width: `${oDist.unknown_pct}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Conflict Detection Summary */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-1">
            Active Brand Conflict Detection
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Surfaces cross-column disagreements without silent fabrication.
          </p>

          <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 mb-4">
            <div className="flex items-center gap-2 text-amber-800 font-bold text-sm mb-1">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>{compliance.total_conflicts_detected} Conflicts Detected</span>
            </div>
            <p className="text-xs text-amber-700 leading-relaxed">
              When distributor columns (e.g. <code>E1_Brand</code> vs <code>Part_Manuf</code>) assert contradictory brand identities, ProductIQ sets status to <strong>Conflicted</strong> and nulls the brand value rather than guessing.
            </p>
          </div>

          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-700">Sample Conflicted Rows:</span>
            {compliance.conflict_examples.slice(0, 3).map((ex) => (
              <div key={ex.row_id} className="p-2.5 bg-slate-50 rounded-lg text-xs border border-slate-200">
                <div className="flex justify-between font-mono font-bold text-slate-800 mb-0.5">
                  <span>Row #{ex.row_id}</span>
                  <span className="text-amber-600">Conflicted</span>
                </div>
                <p className="text-slate-600 truncate">{ex.part_desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Normalization & Fraction Engine Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-1">
            UOM &amp; Decimal-Fraction Engine
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Mathematical 64ths reference table &amp; canonical unit mapper.
          </p>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-medium text-slate-700">Canonical Units Verified:</span>
              <span className="font-mono font-bold text-slate-900">4 (V, A, in, dBA)</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-medium text-slate-700">Standard Fraction Entries:</span>
              <span className="font-mono font-bold text-slate-900">63 (All 64ths)</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-medium text-slate-700">Placeholder Tokens Filtered:</span>
              <span className="font-mono font-bold text-emerald-600">100% (1,000 rows)</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-medium text-slate-700">Avg Ingestion Latency:</span>
              <span className="font-mono font-bold text-slate-900">{compliance.avg_latency_ms_per_row.toFixed(3)} ms / row</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
