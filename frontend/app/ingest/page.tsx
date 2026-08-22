"use client";

import React, { useState } from "react";
import Link from "next/link";
import { PipelineVisualizer } from "@/components/ui/PipelineVisualizer";
import {
  FileText,
  Database,
  Globe,
  Play,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Layers,
  Info,
  RefreshCw,
  Table,
} from "lucide-react";

interface PipelineStageState {
  id: string;
  name: string;
  status: "COMPLETE" | "RUNNING" | "PENDING" | "FAILED";
  records?: number;
  duration_s?: number;
}

const INITIAL_STAGES: PipelineStageState[] = [
  { id: "upload", name: "1. Raw Intake", status: "COMPLETE", records: 3, duration_s: 0.1 },
  { id: "extract", name: "2. Evidence Extraction", status: "COMPLETE", records: 1837, duration_s: 1.2 },
  { id: "normalize", name: "3. Canonical Normalization", status: "COMPLETE", records: 12, duration_s: 0.4 },
  { id: "validate", name: "4. Physics Validation", status: "COMPLETE", records: 409, duration_s: 0.8 },
  { id: "enrich", name: "5. Grounded AI Enrichment", status: "COMPLETE", records: 87, duration_s: 2.5 },
  { id: "trust", name: "6. Trust Intelligence", status: "COMPLETE", records: 62, duration_s: 0.3 },
];

export default function IngestionPage() {
  const [stages, setStages] = useState<PipelineStageState[]>(INITIAL_STAGES);
  const [isReplaying, setIsReplaying] = useState<boolean>(false);
  const [activeStageIndex, setActiveStageIndex] = useState<number>(-1);

  const handleRunReplay = async () => {
    if (isReplaying) return;
    setIsReplaying(true);

    // Reset stages to pending
    const resetStages = INITIAL_STAGES.map((s, idx) => ({
      ...s,
      status: idx === 0 ? ("RUNNING" as const) : ("PENDING" as const),
    }));
    setStages(resetStages);
    setActiveStageIndex(0);

    for (let i = 0; i < INITIAL_STAGES.length; i++) {
      setActiveStageIndex(i);
      setStages((prev) =>
        prev.map((st, idx) => ({
          ...st,
          status: idx < i ? "COMPLETE" : idx === i ? "RUNNING" : "PENDING",
        }))
      );

      // Simulate stage execution delay
      await new Promise((resolve) => setTimeout(resolve, 450));

      setStages((prev) =>
        prev.map((st, idx) => ({
          ...st,
          status: idx <= i ? "COMPLETE" : "PENDING",
        }))
      );
    }

    setIsReplaying(false);
    setActiveStageIndex(-1);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="px-2 py-0.5 text-xs font-bold font-mono uppercase bg-brand-dark/10 text-brand-dark rounded">
            Pipeline Visualizer
          </span>
          <span className="text-xs text-slate-500 font-medium">Demonstration Engine</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Data Ingestion &amp; Pipeline Engine
        </h1>
        <p className="text-slate-600 mt-1 max-w-3xl text-sm">
          Interactive telemetry demonstrating ProductIQ&apos;s 6-stage deterministic extraction, physics validation, and trust scoring pipeline.
        </p>
      </div>

      {/* Honest Prototype Disclosure Card */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-md border border-slate-800 space-y-4">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-brand-accent/20 text-brand-accent flex items-center justify-center shrink-0 mt-0.5">
            <Info className="w-5 h-5" />
          </div>
          <div className="space-y-2">
            <h3 className="text-base font-bold text-white">
              Demonstration Mode &amp; Prototype Boundaries
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              This demonstration replays the pipeline stages using the pre-processed hackathon dataset. Live arbitrary file upload is not enabled in this prototype build to preserve verified source provenance and deterministic evaluation boundaries. Full batch metrics and downloadable outputs are available via the Catalog Dashboard.
            </p>
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={handleRunReplay}
                disabled={isReplaying}
                className="inline-flex items-center gap-2 px-4 py-2 bg-brand-accent hover:bg-brand-accent/90 text-white text-xs font-semibold rounded-lg shadow transition disabled:opacity-50"
              >
                {isReplaying ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Replaying Stage {activeStageIndex + 1} of 6...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Run Demo Pipeline Replay</span>
                  </>
                )}
              </button>

              <Link
                href="/catalog"
                className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold rounded-lg border border-white/20 transition"
              >
                <Table className="w-3.5 h-3.5" />
                <span>Open Catalog Dashboard (1,000 Items) →</span>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Active Pipeline Visualizer Component */}
      <PipelineVisualizer stages={stages} />

      {/* Extraction Precision Analysis Comparison */}
      <div className="space-y-4">
        <div>
          <h3 className="font-sans font-bold text-slate-900 text-lg">
            Extraction Precision Analysis
          </h3>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Comparison between naive generic LLM scrapers vs ProductIQ deterministic normalization.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card A: Standard Generic Scrapers */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-500 uppercase tracking-wider pb-3 border-b border-slate-100">
              <span className="w-2 h-2 rounded-full bg-slate-400" />
              <span>Standard Generic Scrapers / Naive LLM</span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 font-mono text-xs space-y-2 border border-slate-200 text-slate-700">
              <div className="text-slate-500 text-[11px]">
                Input String: &ldquo;W22 Severe Process 1.1kW 4P 400V 50Hz 1420RPM IP55&rdquo;
              </div>
              <div className="flex justify-between pt-2 border-t border-slate-200">
                <span>rated_power:</span>
                <span className="text-slate-800">1.1kW (Unparsed string)</span>
              </div>
              <div className="flex justify-between">
                <span>rated_current:</span>
                <span className="text-rose-600 font-bold">NULL (Missed column)</span>
              </div>
              <div className="flex justify-between">
                <span>rated_speed:</span>
                <span className="text-slate-800">1420 (Unit omitted)</span>
              </div>
              <div className="flex justify-between">
                <span>conflict_detection:</span>
                <span className="text-rose-600">NONE (Silent winner picked)</span>
              </div>
            </div>

            <p className="text-xs text-rose-700 font-sans flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Missed implicit relationships, lost units &amp; silent conflict hallucination.</span>
            </p>
          </div>

          {/* Card B: ProductIQ Deterministic Intelligence */}
          <div className="bg-white rounded-2xl border-2 border-brand-accent/40 p-6 shadow-sm space-y-4 bg-brand-accent/5">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-brand-dark uppercase tracking-wider pb-3 border-b border-brand-accent/20">
              <Sparkles className="w-4 h-4 text-brand-accent" />
              <span>ProductIQ Deterministic Intelligence Engine</span>
            </div>

            <div className="p-4 rounded-xl bg-white font-mono text-xs space-y-2 border border-brand-accent/20 text-slate-900 shadow-sm">
              <div className="text-brand-dark font-medium text-[11px]">
                Input String: &ldquo;W22 Severe Process 1.1kW 4P 400V 50Hz 1420RPM IP55&rdquo;
              </div>
              <div className="flex justify-between pt-2 border-t border-slate-100">
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
              <span>Deterministic normalization, strict canonical units &amp; human review queue generated.</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
