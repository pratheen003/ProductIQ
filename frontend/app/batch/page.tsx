"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { BatchSummary } from "@/lib/types";
import { MetricCard } from "@/components/ui/MetricCard";
import { TrustDistributionChart } from "@/components/charts/TrustDistributionChart";
import { PublishabilityDonut } from "@/components/charts/PublishabilityDonut";
import { SeverityBarChart } from "@/components/charts/SeverityBarChart";
import { ScoreHistogramChart } from "@/components/charts/ScoreHistogramChart";
import { TrustStatusBadge } from "@/components/ui/TrustStatusBadge";
import { PublishabilityBadge } from "@/components/ui/PublishabilityBadge";
import {
  BarChart3,
  Download,
  Play,
  Layers,
  ShieldCheck,
  AlertTriangle,
  FileSpreadsheet,
  ArrowRight,
  RefreshCw,
} from "lucide-react";

export default function BatchIntelligencePage() {
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadBatch() {
      try {
        setLoading(true);
        const data = await api.getBatchSummary();
        setSummary(data);
      } catch (err) {
        console.error("Batch load error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadBatch();
  }, []);

  const handleExportJSON = () => {
    if (!summary) return;
    const blob = new Blob([JSON.stringify(summary, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `productiq_batch_trust_report_${Date.now()}.json`;
    a.click();
  };

  if (loading || !summary) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/4" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-gray-200 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Batch Header Bar (Reference Design Page 3) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-gray-200 shadow-card">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold font-sans text-gray-900 tracking-tight">
              Batch Intelligence Dashboard
            </h2>
            <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-brand-dark text-white">
              BATCH-WEG-W22-IE3
            </span>
          </div>
          <p className="text-xs text-gray-500 font-sans mt-1">
            Aggregated dataset audit across 12 WEG W22 Severe Process induction motors
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportJSON}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-800 border border-gray-200 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Report JSON</span>
          </button>

          <Link
            href="/ingest"
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-brand-accent hover:bg-brand-accentHover text-white shadow-sm transition-all"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Run Pipeline Ingestion</span>
          </Link>
        </div>
      </div>

      {/* 4 Top Cards (Reference Design Page 3) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="PROCESSED"
          value={summary.total_products}
          subtitle="Real manufacturer records"
          badgeText="↑ 100% Extracted"
          badgeType="positive"
        />
        <MetricCard
          title="COMPLETENESS"
          value="100.0%"
          subtitle="All 11 technical fields mapped"
          badgeText="High Density"
          badgeType="positive"
        />
        <MetricCard
          title="AVG TRUST SCORE"
          value={`${(summary.avg_trust_score * 100).toFixed(1)} / 100`}
          subtitle="Deterministic formula S"
          badgeText="Penalized Conflicts"
          badgeType="warning"
        />
        <MetricCard
          title="ISSUES DETECTED"
          value={summary.total_review_items}
          subtitle="Discrepancies & warnings"
          badgeText="62 Review Items"
          badgeType="negative"
        />
      </div>

      {/* Visual Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrustDistributionChart data={summary.trust_distribution} />
        <PublishabilityDonut data={summary.publishability_distribution} />
        <SeverityBarChart data={summary.severity_distribution} />
        <ScoreHistogramChart products={summary.products} />
      </div>

      {/* Full 12-Product Batch Audit Matrix */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-card overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="font-sans font-bold text-gray-900 text-base">
              Dataset Motor Inventory & Conflict Audit
            </h3>
            <p className="text-xs text-gray-500 font-sans mt-0.5">
              Side-by-side comparison of all 12 motors in the batch
            </p>
          </div>
          <span className="font-mono text-xs text-gray-500">
            12 of 12 motors require review before publishing
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 border-b border-gray-100 font-mono text-[11px] text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-6 font-semibold">SKU / Model</th>
                <th className="py-3 px-6 font-semibold">Power</th>
                <th className="py-3 px-6 font-semibold">Speed</th>
                <th className="py-3 px-6 font-semibold">Trust Score</th>
                <th className="py-3 px-6 font-semibold">Data Quality</th>
                <th className="py-3 px-6 font-semibold">Catalog Readiness</th>
                <th className="py-3 px-6 font-semibold">Flagged Conflicts</th>
                <th className="py-3 px-6 font-semibold text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {summary.products.map((p) => (
                <tr key={p.product_id} className="hover:bg-gray-50/80 transition-colors">
                  <td className="py-4 px-6 font-mono font-bold text-gray-900">
                    <Link
                      href={`/products/${p.product_id}`}
                      className="hover:text-brand-accent transition-colors"
                    >
                      {p.product_id}
                    </Link>
                  </td>
                  <td className="py-4 px-6 font-mono text-gray-800">
                    {p.rated_power_kw ? `${p.rated_power_kw} kW` : "—"}
                  </td>
                  <td className="py-4 px-6 font-mono text-gray-600">
                    {p.rated_speed_rpm ? `${p.rated_speed_rpm} RPM` : "—"}
                  </td>
                  <td className="py-4 px-6 font-mono font-bold">
                    <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-900">
                      {(p.trust_score * 100).toFixed(1)}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <TrustStatusBadge status={p.overall_trust_status} size="sm" />
                  </td>
                  <td className="py-4 px-6">
                    <PublishabilityBadge status={p.overall_publishability} />
                  </td>
                  <td className="py-4 px-6 font-mono text-rose-600 font-semibold">
                    {p.conflicts_count} conflicts
                  </td>
                  <td className="py-4 px-6 text-right">
                    <Link
                      href={`/products/${p.product_id}`}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-brand-accent hover:text-white text-gray-700 transition-all inline-flex items-center gap-1"
                    >
                      <span>Inspect</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
