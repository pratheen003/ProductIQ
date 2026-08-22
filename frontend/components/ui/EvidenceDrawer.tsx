"use client";

import React from "react";
import { EvidenceRecord } from "@/lib/types";
import { FileText, Database, Globe, Sparkles, CheckCircle2, ChevronRight } from "lucide-react";

interface EvidenceDrawerProps {
  attribute: string;
  records: EvidenceRecord[];
  className?: string;
}

export function EvidenceDrawer({
  attribute,
  records,
  className = "",
}: EvidenceDrawerProps) {
  const filtered = records.filter(
    (r) => r.attribute.toLowerCase() === attribute.toLowerCase()
  );

  if (filtered.length === 0) {
    return (
      <div className={`p-4 bg-gray-50 rounded-lg border border-gray-200 text-xs text-gray-500 font-sans ${className}`}>
        No raw source evidence records found for &apos;{attribute}&apos;.
      </div>
    );
  }

  const getSourceIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "pdf":
        return <FileText className="w-4 h-4 text-blue-600" />;
      case "csv":
        return <Database className="w-4 h-4 text-amber-600" />;
      case "web":
        return <Globe className="w-4 h-4 text-emerald-600" />;
      default:
        return <Sparkles className="w-4 h-4 text-purple-600" />;
    }
  };

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 shadow-subtle ${className}`}>
      <div className="flex items-center justify-between pb-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-800 font-sans">
            Verified Source Provenance Chain
          </span>
          <span className="text-[10px] font-mono bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
            {filtered.length} Record{filtered.length > 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <div className="mt-3 space-y-2.5">
        {filtered.map((rec, idx) => (
          <div
            key={idx}
            className="p-3 rounded-lg bg-gray-50/80 border border-gray-100 flex flex-col gap-1.5 hover:bg-gray-50 transition-colors text-xs"
          >
            <div className="flex items-center justify-between font-mono">
              <div className="flex items-center gap-2">
                {getSourceIcon(rec.source_type)}
                <span className="font-bold text-gray-800 uppercase text-[11px]">
                  {rec.source_id} ({rec.source_type})
                </span>
              </div>
              <span className="text-[11px] text-gray-500">
                {rec.page ? `Page ${rec.page}` : rec.row ? `Row ${rec.row}` : "Web URL"}
              </span>
            </div>

            <div className="flex items-center justify-between font-mono bg-white p-2 rounded border border-gray-100">
              <span className="text-gray-600">Extracted Raw:</span>
              <span className="font-bold text-gray-900">
                &ldquo;{rec.raw_value} {rec.raw_unit || ""}&rdquo;
              </span>
            </div>

            {rec.evidence_text && (
              <p className="text-[11px] text-gray-500 font-sans italic line-clamp-2">
                &ldquo;{rec.evidence_text}&rdquo;
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
