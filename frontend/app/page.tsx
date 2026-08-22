"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { BatchSummary, ProductSummary } from "@/lib/types";
import { MetricCard } from "@/components/ui/MetricCard";
import { TrustDistributionChart } from "@/components/charts/TrustDistributionChart";
import { PublishabilityDonut } from "@/components/charts/PublishabilityDonut";
import { SeverityBarChart } from "@/components/charts/SeverityBarChart";
import { ScoreHistogramChart } from "@/components/charts/ScoreHistogramChart";
import { TrustStatusBadge } from "@/components/ui/TrustStatusBadge";
import { PublishabilityBadge } from "@/components/ui/PublishabilityBadge";
import {
  Database,
  ShieldCheck,
  AlertTriangle,
  Layers,
  ArrowRight,
  Sparkles,
  Activity,
  CheckCircle2,
  FileText,
} from "lucide-react";

export default function DashboardPage() {
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        const [batchData, productsData] = await Promise.all([
          api.getBatchSummary(),
          api.getProducts(),
        ]);
        setSummary(batchData);
        setProducts(productsData);
      } catch (err: any) {
        console.error("Dashboard error:", err);
        setError(err.message || "Failed to load dashboard data from backend.");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/4" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-gray-200 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-64 bg-gray-200 rounded-xl" />
          <div className="h-64 bg-gray-200 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="p-8 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800">
        <h3 className="font-bold text-lg font-sans">Unable to connect to ProductIQ API</h3>
        <p className="text-xs mt-1">{error || "Backend service is not responding on port 8000."}</p>
        <div className="mt-4">
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-rose-600 text-white rounded-lg text-xs font-semibold"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Top Banner / Headline */}
      <div className="bg-gradient-to-r from-brand-dark via-brand-darker to-brand-darkest text-white rounded-2xl p-6 sm:p-8 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-6 relative overflow-hidden">
        <div className="space-y-2 z-10">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-brand-accent/30 text-brand-muted border border-brand-accent/40 uppercase">
              Phase 6 Enterprise UI
            </span>
            <span className="text-xs text-white/60 font-mono">
              Dataset: 12 WEG W22 Motors
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold font-sans tracking-tight">
            Deterministic Product Intelligence
          </h2>
          <p className="text-sm text-white/80 max-w-2xl font-sans">
            Continuous cross-source validation, mathematical trust scoring, and human-in-the-loop conflict resolution for industrial catalogs.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 z-10 shrink-0">
          <Link
            href="/products/PIQ-W22SP-4P-1.1"
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-brand-accent hover:bg-brand-accentHover text-white text-xs font-semibold shadow-md flex items-center justify-center gap-2 transition-all"
          >
            <span>Inspect Hard-Gate Conflict</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/reviews"
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold border border-white/20 flex items-center justify-center gap-2 transition-all"
          >
            <span>Review Queue ({summary.total_review_items})</span>
          </Link>
        </div>
      </div>

      {/* Top Real Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Motors Processed"
          value={summary.total_products}
          subtitle="Real WEG W22 motors"
          badgeText="100% Extracted"
          badgeType="positive"
          icon={Database}
        />
        <MetricCard
          title="Avg Trust Score"
          value={`${(summary.avg_trust_score * 100).toFixed(1)} / 100`}
          subtitle="Deterministic formula"
          badgeText="Penalized Conflicts"
          badgeType="warning"
          icon={ShieldCheck}
        />
        <MetricCard
          title="Conflicted Motors"
          value={summary.conflicted_count}
          subtitle="Preserved discrepancies"
          badgeText="Zero Silent Winners"
          badgeType="negative"
          icon={AlertTriangle}
        />
        <MetricCard
          title="Review Queue Items"
          value={summary.total_review_items}
          subtitle="Awaiting domain engineer"
          badgeText="Actionable Queue"
          badgeType="brand"
          icon={Layers}
        />
      </div>

      {/* Visual Analytics Grid (Recharts) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrustDistributionChart data={summary.trust_distribution} />
        <PublishabilityDonut data={summary.publishability_distribution} />
        <SeverityBarChart data={summary.severity_distribution} />
        <ScoreHistogramChart products={products} />
      </div>

      {/* Flagged Products Quick Action Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-card overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="font-sans font-bold text-gray-900 text-base">
              Catalog Products & Verification Summary
            </h3>
            <p className="text-xs text-gray-500 font-sans mt-0.5">
              Live trust tier classification and catalog publishability gates
            </p>
          </div>
          <Link
            href="/products"
            className="text-xs font-semibold text-brand-accent hover:text-brand-accentHover flex items-center gap-1 transition-colors"
          >
            <span>View All 12 Motors</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 border-b border-gray-100 font-mono text-[11px] text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-6 font-semibold">SKU / Product ID</th>
                <th className="py-3 px-6 font-semibold">Power (kW)</th>
                <th className="py-3 px-6 font-semibold">Trust Score</th>
                <th className="py-3 px-6 font-semibold">Data Quality</th>
                <th className="py-3 px-6 font-semibold">Catalog Readiness</th>
                <th className="py-3 px-6 font-semibold">Reviews</th>
                <th className="py-3 px-6 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {products.slice(0, 6).map((p) => (
                <tr key={p.product_id} className="hover:bg-gray-50/80 transition-colors">
                  <td className="py-4 px-6 font-mono font-bold text-gray-900">
                    <Link
                      href={`/products/${p.product_id}`}
                      className="hover:text-brand-accent transition-colors"
                    >
                      {p.product_id}
                    </Link>
                  </td>
                  <td className="py-4 px-6 font-mono text-gray-700">
                    {p.rated_power_kw ? `${p.rated_power_kw} kW` : "—"}
                  </td>
                  <td className="py-4 px-6 font-mono font-bold">
                    <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-800">
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
                    {p.review_items_count} items
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
