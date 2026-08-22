"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Sparkles,
  ArrowRight,
  RefreshCw,
  FileCheck,
  ShieldAlert,
  Info,
} from "lucide-react";
import { api } from "@/lib/api";
import { CatalogExactMatchEvalDTO } from "@/lib/types";

export default function CatalogGoldStandardPage() {
  const [data, setData] = useState<CatalogExactMatchEvalDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEval = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCatalogExactMatchEval();
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load gold standard evaluation");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEval();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-brand-accent animate-spin" />
          <p className="text-sm text-slate-500 font-medium">Loading Gold Standard evaluation (n=2)...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8">
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-rose-700">
          <h3 className="font-semibold text-lg mb-2">Error Loading Gold Standard Evaluation</h3>
          <p className="text-sm mb-4">{error || "Could not retrieve gold standard data."}</p>
          <button
            onClick={loadEval}
            className="px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-medium hover:bg-rose-700 transition"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 text-xs font-bold font-mono uppercase bg-emerald-100 text-emerald-800 rounded">
              Mechanism A Evaluation
            </span>
            <span className="text-xs font-mono font-bold text-slate-500">{data.sample_size_label}</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Gold Standard Proof View
          </h1>
          <p className="text-slate-600 mt-1">
            Field-by-field verification of pipeline output against Unilog&apos;s expected delivery format.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-right">
            <span className="text-[10px] uppercase font-bold text-emerald-700 block">Fidelity Score</span>
            <span className="text-2xl font-black text-emerald-600 font-mono">{data.overall_exact_match_rate_pct}%</span>
          </div>
        </div>
      </div>

      {/* Mandatory Corrected Framing & Disclaimer Box */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-md border border-slate-800 space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
            <Info className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">
              {data.metric_label}
            </h3>
            <p className="text-xs text-slate-400">
              Scoped Scored Fields: {data.total_fields_matched} / {data.total_fields_compared} Matched Exactly
            </p>
          </div>
        </div>

        <div className="p-4 bg-white/5 rounded-xl border border-white/10 text-xs text-slate-300 leading-relaxed font-sans">
          <span className="font-bold text-emerald-400">Documentation Invariant:</span> {data.disclaimer}
        </div>
      </div>

      {/* Gold Rows Side-by-Side Detail */}
      <div className="space-y-8">
        {data.rows.map((row) => (
          <div key={row.row_id} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {/* Row Card Header */}
            <div className="p-5 bg-slate-50 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-xs bg-slate-200 px-2 py-0.5 rounded text-slate-700">
                    Gold Row #{row.row_id}
                  </span>
                  <h3 className="text-lg font-bold font-mono text-slate-900">
                    {row.mfg_part_num}
                  </h3>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Compared across {row.fields_compared} scoped delivery fields
                </p>
              </div>

              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-xs font-bold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  {row.row_accuracy_pct}% Match ({row.fields_matched}/{row.fields_compared})
                </span>
                <Link
                  href={`/catalog/products/${row.row_id}`}
                  className="px-3 py-1 bg-white border border-slate-200 text-xs font-semibold rounded-lg hover:bg-slate-50 transition"
                >
                  Full Product View →
                </Link>
              </div>
            </div>

            {/* Field Comparison Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-100 text-slate-600 uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-4 w-1/4">Delivery Field</th>
                    <th className="py-3 px-4 w-1/3">ProductIQ Pipeline Output</th>
                    <th className="py-3 px-4 w-1/3">Ground Truth Delivery Expected</th>
                    <th className="py-3 px-4 text-center">Match</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {row.field_comparisons.map((c, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/70">
                      <td className="py-3 px-4 font-mono font-semibold text-slate-900">
                        {c.field_name}
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-800">
                        <span className="font-semibold">{c.pipeline_value || "null"}</span>
                        <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded font-mono font-bold">
                          {c.status_tier}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-600">
                        <span className="font-semibold">{c.expected_value || "null"}</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        {c.is_exact_match ? (
                          <span className="inline-flex items-center gap-1 font-bold text-emerald-600">
                            <CheckCircle2 className="w-4 h-4" />
                            EXACT
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 font-bold text-rose-600">
                            DIFF
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
