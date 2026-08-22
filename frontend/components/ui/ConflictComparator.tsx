"use client";

import React from "react";
import {
  AlertTriangle,
  FileText,
  Database,
  Globe,
  ShieldAlert,
  ArrowRight,
  HelpCircle,
} from "lucide-react";
import { TrustStatusBadge } from "./TrustStatusBadge";
import { ConflictRecord, ConflictSource } from "@/lib/types";

interface ConflictComparatorProps {
  field: string;
  conflict?: ConflictRecord;
  conflicts?: any[];
  sources?: ConflictSource[];
  description?: string;
  recommendedAction?: string;
  onResolveClick?: () => void;
  className?: string;
}

export function ConflictComparator({
  field,
  conflict,
  conflicts,
  sources: directSources,
  description,
  recommendedAction,
  onResolveClick,
  className = "",
}: ConflictComparatorProps) {
  // Normalize sources from all possible input contracts (N-source list-based)
  const normalizedSources: ConflictSource[] = [];

  if (directSources && directSources.length > 0) {
    normalizedSources.push(...directSources);
  } else if (conflict?.sources && conflict.sources.length > 0) {
    normalizedSources.push(...conflict.sources);
  } else if (conflicts && conflicts.length > 0) {
    const first = conflicts[0];
    if (first?.sources && Array.isArray(first.sources) && first.sources.length > 0) {
      normalizedSources.push(...first.sources);
    } else if (first?.source_a || first?.source_b) {
      // Legacy pairwise fallback
      if (first.source_a) {
        normalizedSources.push({
          source_type: String(first.source_a).toLowerCase(),
          source_name: `${String(first.source_a).toUpperCase()} Source`,
          value: first.value_a,
          unit: first.unit_a,
          raw_value: first.raw_a ? String(first.raw_a) : undefined,
          location: "Primary Document",
        });
      }
      if (first.source_b) {
        normalizedSources.push({
          source_type: String(first.source_b).toLowerCase(),
          source_name: `${String(first.source_b).toUpperCase()} Source`,
          value: first.value_b,
          unit: first.unit_b,
          raw_value: first.raw_b ? String(first.raw_b) : undefined,
          location: "Secondary Document",
        });
      }
    }
  }

  const effectiveDescription =
    description ||
    conflict?.description ||
    (conflicts && conflicts[0]?.description) ||
    `Discrepancy detected across ${normalizedSources.length || "multiple"} independent authoritative sources.`;

  const effectiveAction =
    recommendedAction ||
    conflict?.recommended_action ||
    conflict?.action_needed ||
    (conflicts && conflicts[0]?.action_needed) ||
    "Inspect physical nameplate or official dimension drawing before catalog publishing.";

  const getSourceIcon = (type?: string) => {
    const t = (type || "").toLowerCase();
    if (t.includes("pdf")) return <FileText className="w-4 h-4 text-blue-600" />;
    if (t.includes("csv")) return <Database className="w-4 h-4 text-amber-600" />;
    if (t.includes("web")) return <Globe className="w-4 h-4 text-emerald-600" />;
    return <HelpCircle className="w-4 h-4 text-gray-500" />;
  };

  const getSourceBadgeColor = (type?: string) => {
    const t = (type || "").toLowerCase();
    if (t.includes("pdf")) return "bg-blue-50 text-blue-700 border-blue-200";
    if (t.includes("csv")) return "bg-amber-50 text-amber-700 border-amber-200";
    if (t.includes("web")) return "bg-emerald-50 text-emerald-700 border-emerald-200";
    return "bg-gray-100 text-gray-700 border-gray-200";
  };

  return (
    <div
      className={`rounded-xl border-2 border-rose-200 bg-rose-50/40 p-5 shadow-card ${className}`}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-rose-200/80">
        <div className="flex items-start sm:items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-rose-500 text-white flex items-center justify-center shadow-sm shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono font-bold text-gray-900 text-base">
                {field}
              </span>
              <TrustStatusBadge status="CONFLICTED" size="sm" />
              <span className="text-[10px] font-mono font-semibold bg-rose-100 text-rose-800 px-2 py-0.5 rounded border border-rose-300">
                {normalizedSources.length} Disagreeing Sources
              </span>
            </div>
            <p className="text-xs text-rose-800 font-sans mt-0.5">
              Hard-Gate Preserved — Zero Arbitrary Winner Selected (Canonical = null)
            </p>
          </div>
        </div>

        {onResolveClick && (
          <button
            onClick={onResolveClick}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-all self-start sm:self-auto shrink-0"
          >
            <span>Review & Resolve</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Description */}
      {effectiveDescription && (
        <div className="mt-3 text-xs font-sans text-gray-700 leading-relaxed bg-white/60 p-3 rounded-lg border border-rose-100">
          <span className="font-semibold text-gray-900">Finding: </span>
          <span>{effectiveDescription}</span>
        </div>
      )}

      {/* Dynamic N-Source Comparison Grid */}
      {normalizedSources.length > 0 ? (
        <div
          className={`mt-4 grid grid-cols-1 ${
            normalizedSources.length === 1
              ? "md:grid-cols-1"
              : normalizedSources.length === 2
              ? "md:grid-cols-2"
              : "md:grid-cols-3"
          } gap-4`}
        >
          {normalizedSources.map((src, idx) => {
            const typeStr = (src.source_type || "source").toLowerCase();
            const nameStr = src.source_name || `${typeStr.toUpperCase()} Source`;
            const displayVal =
              src.value !== null && src.value !== undefined
                ? `${src.value} ${src.unit || ""}`.trim()
                : src.raw_value || "null";

            return (
              <div
                key={idx}
                className="bg-white rounded-xl border border-gray-200 p-4 shadow-subtle flex flex-col justify-between hover:border-brand-accent/40 transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between text-xs font-mono text-gray-500 pb-2.5 border-b border-gray-100">
                    <div className="flex items-center gap-1.5 text-brand-dark font-semibold truncate">
                      {getSourceIcon(typeStr)}
                      <span className="uppercase text-[11px] font-mono tracking-tight truncate">
                        {nameStr}
                      </span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold border shrink-0 ${getSourceBadgeColor(
                        typeStr
                      )}`}
                    >
                      {typeStr}
                    </span>
                  </div>

                  <div className="mt-3.5">
                    <div className="text-2xl font-mono font-bold text-gray-900 tracking-tight">
                      {displayVal}
                    </div>
                    {src.raw_value && (
                      <p className="text-[11px] font-mono text-gray-500 mt-1">
                        Raw literal: &ldquo;{src.raw_value}&rdquo;
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-4 pt-2.5 text-[11px] text-gray-500 font-sans border-t border-gray-100 flex items-center justify-between">
                  <span className="truncate" title={src.location || src.source_id}>
                    {src.location || src.source_id || "Recorded Provenance"}
                  </span>
                  {src.confidence !== undefined && src.confidence !== null && (
                    <span className="font-mono text-[10px] text-gray-400 shrink-0 ml-2">
                      Conf: {Math.round(src.confidence * 100)}%
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="mt-4 p-4 rounded-xl bg-white border border-gray-200 text-xs text-gray-600 font-sans">
          No detailed source records available for this conflict. Verification required.
        </div>
      )}

      {/* Recommended Action Footer */}
      {effectiveAction && (
        <div className="mt-4 p-3.5 rounded-lg bg-white/90 border border-rose-200/80 flex items-start gap-2.5 text-xs text-gray-800">
          <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-gray-900">
              Recommended Engineering Action:{" "}
            </span>
            <span className="text-gray-700">{effectiveAction}</span>
          </div>
        </div>
      )}
    </div>
  );
}
