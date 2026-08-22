"use client";

import React, { useState } from "react";
import { api } from "@/lib/api";
import { PipelineVisualizer } from "@/components/ui/PipelineVisualizer";
import {
  Upload,
  FileText,
  Database,
  Globe,
  Play,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Layers,
} from "lucide-react";

export default function IngestionPage() {
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [pipelineResult, setPipelineResult] = useState<any | null>(null);

  const handleRunDemoPipeline = async () => {
    try {
      setIsProcessing(true);
      const res = await api.triggerDemoIngest();
      setPipelineResult(res);
    } catch (err) {
      console.error("Pipeline run error:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header (Reference Design Page 1) */}
      <div>
        <h2 className="text-2xl font-bold font-sans text-gray-900 tracking-tight">
          Data Ingestion Engine
        </h2>
        <p className="text-xs text-gray-500 font-sans mt-1 max-w-3xl">
          Drop raw supplier catalogs, unstructured technical PDFs, or legacy CSVs. The ProductIQ engine will extract, normalize, validate, and evaluate trust across product attributes with extreme precision.
        </p>
      </div>

      {/* Drag & Drop Documents Zone (Reference Design Page 1) */}
      <div className="bg-white rounded-2xl border-2 border-dashed border-gray-300 hover:border-brand-accent/60 transition-colors p-10 shadow-card flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 rounded-2xl bg-brand-dark/5 border border-brand-dark/10 flex items-center justify-center text-brand-accent shadow-sm mb-4">
          <Upload className="w-8 h-8" />
        </div>

        <h3 className="text-lg font-bold font-sans text-gray-900">
          Drag & Drop Technical Documents
        </h3>
        <p className="text-xs text-gray-500 font-sans mt-1 max-w-md">
          Supports multi-page manufacturer PDFs, legacy ERP CSVs, and Web catalog URLs (brochures up to 500MB).
        </p>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={handleRunDemoPipeline}
            disabled={isProcessing}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold bg-brand-accent hover:bg-brand-accentHover text-white shadow-md transition-all disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            <span>{isProcessing ? "Processing Pipeline..." : "Execute WEG Dataset Ingest"}</span>
          </button>

          <span className="text-xs text-gray-400 font-sans">or</span>

          <button
            onClick={() => alert("API Webhook active: POST /api/ingest")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-800 border border-gray-200 transition-all"
          >
            <Database className="w-4 h-4 text-brand-dark" />
            <span>Connect ERP / API</span>
          </button>
        </div>

        {/* Source format tags */}
        <div className="mt-6 flex items-center gap-4 text-xs font-mono text-gray-400">
          <span className="flex items-center gap-1">
            <FileText className="w-3.5 h-3.5 text-blue-500" /> PDF Datasheets
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Database className="w-3.5 h-3.5 text-amber-500" /> Legacy CSV / ERP
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Globe className="w-3.5 h-3.5 text-emerald-500" /> Web Catalogs
          </span>
        </div>
      </div>

      {/* Active Pipeline Visualizer */}
      <PipelineVisualizer />

      {/* Extraction Precision Analysis (Reference Design Page 1) */}
      <div className="space-y-4">
        <div>
          <h3 className="font-sans font-bold text-gray-900 text-lg">
            Extraction Precision Analysis
          </h3>
          <p className="text-xs text-gray-500 font-sans mt-0.5">
            Comparison between naive generic LLM scrapers vs ProductIQ deterministic normalization
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card A: Standard Generic Scrapers */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-card space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-gray-500 uppercase tracking-wider pb-3 border-b border-gray-100">
              <span className="w-2 h-2 rounded-full bg-gray-400" />
              <span>Standard Generic Scrapers / Naive Regex</span>
            </div>

            <div className="p-4 rounded-xl bg-gray-50 font-mono text-xs space-y-2 border border-gray-200 text-gray-700">
              <div className="text-gray-500 text-[11px]">
                Input String: &ldquo;W22 Severe Process 1.1kW 4P 400V 50Hz 1420RPM IP55&rdquo;
              </div>
              <div className="flex justify-between pt-2 border-t border-gray-200">
                <span>rated_power:</span>
                <span className="text-gray-800">1.1kW (Unparsed string)</span>
              </div>
              <div className="flex justify-between">
                <span>rated_current:</span>
                <span className="text-rose-600 font-bold">NULL (Missed column)</span>
              </div>
              <div className="flex justify-between">
                <span>rated_speed:</span>
                <span className="text-gray-800">1420 (Unit omitted)</span>
              </div>
              <div className="flex justify-between">
                <span>conflict_detection:</span>
                <span className="text-rose-600">NONE (Silent winner picked)</span>
              </div>
            </div>

            <p className="text-xs text-rose-700 font-sans flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Missed implicit relationships, lost units & silent conflict hallucination.</span>
            </p>
          </div>

          {/* Card B: ProductIQ Deterministic Intelligence */}
          <div className="bg-white rounded-2xl border-2 border-brand-accent/40 p-6 shadow-card space-y-4 bg-brand-accent/5">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-brand-dark uppercase tracking-wider pb-3 border-b border-brand-accent/20">
              <Sparkles className="w-4 h-4 text-brand-accent" />
              <span>ProductIQ Deterministic Intelligence Engine</span>
            </div>

            <div className="p-4 rounded-xl bg-white font-mono text-xs space-y-2 border border-brand-accent/20 text-gray-900 shadow-subtle">
              <div className="text-brand-dark font-medium text-[11px]">
                Input String: &ldquo;W22 Severe Process 1.1kW 4P 400V 50Hz 1420RPM IP55&rdquo;
              </div>
              <div className="flex justify-between pt-2 border-t border-gray-100">
                <span>rated_power:</span>
                <span className="text-emerald-700 font-bold">1.1 kW [VERIFIED]</span>
              </div>
              <div className="flex justify-between">
                <span>rated_current:</span>
                <span className="text-rose-600 font-bold">NULL [CONFLICT: PDF vs CSV]</span>
              </div>
              <div className="flex justify-between">
                <span>rated_speed:</span>
                <span className="text-emerald-700 font-bold">1420.0 RPM [CANONICAL]</span>
              </div>
              <div className="flex justify-between">
                <span>provenance:</span>
                <span className="text-brand-accent font-bold">100% (p.5 table, row 1)</span>
              </div>
            </div>

            <p className="text-xs text-emerald-700 font-sans flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>Deterministic normalization, strict canonical units & human review queue generated.</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
