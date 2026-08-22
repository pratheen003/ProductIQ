"use client";

import React from "react";
import { ReviewItem, ConflictSource } from "@/lib/types";
import { getSeverityConfig } from "@/lib/utils";
import {
  AlertTriangle,
  FileText,
  Database,
  Globe,
  HelpCircle,
  ArrowRight,
  CheckCircle2,
  Cpu,
} from "lucide-react";

interface ReviewItemCardProps {
  item: ReviewItem;
  onResolve: (item: ReviewItem) => void;
  className?: string;
}

export function ReviewItemCard({
  item,
  onResolve,
  className = "",
}: ReviewItemCardProps) {
  const sevConfig = getSeverityConfig(item.severity);
  const isResolved = item.status === "RESOLVED";

  // Normalize sources from conflicting_sources or conflicting_values
  const sources: ConflictSource[] = [];
  if (item.conflicting_sources && item.conflicting_sources.length > 0) {
    sources.push(...item.conflicting_sources);
  } else if (item.conflicting_values && item.conflicting_values.length > 0) {
    const cv = item.conflicting_values[0];
    if (cv.source_a) {
      sources.push({
        source_id: "src_a",
        source_type: String(cv.source_a).toLowerCase(),
        source_name: `${String(cv.source_a).toUpperCase()} Source`,
        value: cv.value_a,
        unit: cv.unit_a,
        raw_value: cv.raw_a,
        location: "Primary Document",
      });
    }
    if (cv.source_b) {
      sources.push({
        source_id: "src_b",
        source_type: String(cv.source_b).toLowerCase(),
        source_name: `${String(cv.source_b).toUpperCase()} Source`,
        value: cv.value_b,
        unit: cv.unit_b,
        raw_value: cv.raw_b,
        location: "Secondary Document",
      });
    }
  }

  const getSourceIcon = (type?: string) => {
    const t = (type || "").toLowerCase();
    if (t.includes("pdf")) return <FileText className="w-4 h-4 text-blue-600" />;
    if (t.includes("csv")) return <Database className="w-4 h-4 text-amber-600" />;
    if (t.includes("web")) return <Globe className="w-4 h-4 text-emerald-600" />;
    return <HelpCircle className="w-4 h-4 text-gray-500" />;
  };

  return (
    <div
      className={`bg-white rounded-xl border ${
        isResolved
          ? "border-emerald-200 bg-emerald-50/10"
          : "border-gray-200 hover:border-gray-300"
      } p-6 shadow-card hover:shadow-elevation transition-all ${className}`}
    >
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-gray-100">
        <div className="flex items-start gap-3.5">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
              isResolved
                ? "bg-emerald-500 text-white"
                : item.issue_type === "CONFLICT"
                ? "bg-rose-500 text-white"
                : "bg-amber-500 text-white"
            }`}
          >
            {isResolved ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : item.issue_type === "CONFLICT" ? (
              <AlertTriangle className="w-5 h-5" />
            ) : (
              <Cpu className="w-5 h-5" />
            )}
          </div>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-sans font-bold text-gray-900 text-base">
                {item.product_id || "Product Review"}
              </span>
              <span className="font-mono text-xs text-gray-500">
                • {item.target_name}
              </span>
              <span
                className={`px-2 py-0.5 text-[11px] font-mono font-semibold rounded border ${sevConfig.color}`}
              >
                {sevConfig.label}
              </span>
              {isResolved && (
                <span className="px-2 py-0.5 text-[11px] font-sans font-semibold rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                  Resolved
                </span>
              )}
            </div>
            <p className="text-xs text-gray-600 font-sans mt-0.5">
              {item.description}
            </p>
          </div>
        </div>

        {/* Review ID */}
        <span className="font-mono text-[11px] text-gray-400 bg-gray-50 px-2 py-1 rounded border border-gray-100 self-start">
          {item.review_id}
        </span>
      </div>

      {/* Conflicting Source Values Box */}
      {sources.length > 0 && (
        <div className="mt-4">
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-gray-500">
            Source Discrepancies ({sources.length})
          </span>

          <div
            className={`mt-2 grid grid-cols-1 ${
              sources.length === 1
                ? "sm:grid-cols-1"
                : sources.length === 2
                ? "sm:grid-cols-2"
                : "sm:grid-cols-3"
            } gap-3`}
          >
            {sources.map((src, idx) => {
              const displayVal =
                src.value !== null && src.value !== undefined
                  ? `${src.value} ${src.unit || ""}`.trim()
                  : src.raw_value || "null";

              return (
                <div
                  key={idx}
                  className="p-3.5 rounded-lg bg-gray-50 border border-gray-200 flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between text-xs font-mono text-gray-500 pb-1.5 border-b border-gray-200/60">
                    <div className="flex items-center gap-1.5 text-gray-800 font-semibold truncate">
                      {getSourceIcon(src.source_type)}
                      <span className="uppercase truncate">
                        {src.source_name || `${(src.source_type || "source").toUpperCase()} Source`}
                      </span>
                    </div>
                  </div>
                  <div className="mt-2 text-xl font-mono font-bold text-gray-900">
                    {displayVal}
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-gray-400">
                    <span>{src.location || "Recorded Provenance"}</span>
                    {src.raw_value && <span>Raw: &ldquo;{src.raw_value}&rdquo;</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Resolution Note if resolved */}
      {isResolved && item.resolution_note && (
        <div className="mt-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 font-sans flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">
              Resolved ({item.resolved_by || "Domain Engineer"}):{" "}
            </span>
            <span>{item.resolution_note}</span>
            {item.resolved_value && (
              <span className="block font-mono font-bold text-emerald-800 mt-0.5">
                Canonical Value: {String(item.resolved_value)}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Footer & Actions */}
      <div className="mt-5 pt-4 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="text-xs text-gray-600 font-sans">
          <span className="font-semibold text-gray-800">Action: </span>
          <span>{item.recommended_action}</span>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
          <button
            onClick={() => onResolve(item)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold shadow-sm transition-all ${
              isResolved
                ? "bg-gray-100 hover:bg-gray-200 text-gray-800"
                : "bg-brand-accent hover:bg-brand-accentHover text-white"
            }`}
          >
            <span>{isResolved ? "View Resolution" : "Review & Resolve"}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
