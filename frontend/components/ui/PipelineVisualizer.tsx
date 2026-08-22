"use client";

import React from "react";
import { CheckCircle2, Loader2, ArrowRight } from "lucide-react";

interface PipelineStage {
  id: string;
  name: string;
  status: "COMPLETE" | "RUNNING" | "PENDING" | "FAILED";
  records?: number;
  duration_s?: number;
}

interface PipelineVisualizerProps {
  stages?: PipelineStage[];
  className?: string;
}

const DEFAULT_STAGES: PipelineStage[] = [
  { id: "upload", name: "1. Raw Intake", status: "COMPLETE", records: 3, duration_s: 0.1 },
  { id: "extract", name: "2. Evidence Extraction", status: "COMPLETE", records: 1837, duration_s: 1.2 },
  { id: "normalize", name: "3. Canonical Normalization", status: "COMPLETE", records: 12, duration_s: 0.4 },
  { id: "validate", name: "4. Physics Validation", status: "COMPLETE", records: 409, duration_s: 0.8 },
  { id: "enrich", name: "5. Grounded AI Enrichment", status: "COMPLETE", records: 87, duration_s: 2.5 },
  { id: "trust", name: "6. Trust Intelligence", status: "COMPLETE", records: 62, duration_s: 0.3 },
];

export function PipelineVisualizer({
  stages = DEFAULT_STAGES,
  className = "",
}: PipelineVisualizerProps) {
  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-6 shadow-card ${className}`}>
      <div className="flex items-center justify-between pb-4 border-b border-gray-100">
        <div>
          <h4 className="font-sans font-bold text-gray-900 text-sm">
            ProductIQ Deterministic Intelligence Pipeline
          </h4>
          <p className="text-xs text-gray-500 font-sans mt-0.5">
            Real-time telemetry across multi-stage extraction, validation & trust scoring
          </p>
        </div>
        <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Pipeline Active</span>
        </span>
      </div>

      <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {stages.map((st, idx) => (
          <div
            key={st.id}
            className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/70 flex flex-col justify-between relative group hover:border-brand-accent/40 transition-colors"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-brand-dark/60 uppercase">
                  Stage 0{idx + 1}
                </span>
                {st.status === "COMPLETE" ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : st.status === "RUNNING" ? (
                  <Loader2 className="w-4 h-4 text-brand-accent animate-spin" />
                ) : (
                  <span className="w-3 h-3 rounded-full bg-gray-300" />
                )}
              </div>
              <h5 className="text-xs font-sans font-bold text-gray-900 mt-2 leading-tight">
                {st.name}
              </h5>
            </div>

            <div className="mt-4 pt-2 border-t border-gray-200/60 flex items-center justify-between text-[10px] font-mono text-gray-500">
              <span>{st.records ? `${st.records} items` : "Active"}</span>
              <span>{st.duration_s ? `${st.duration_s}s` : ""}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
