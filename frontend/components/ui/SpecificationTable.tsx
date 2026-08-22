"use client";

import React, { useState } from "react";
import { Specification, EvidenceRecord, ConflictRecord } from "@/lib/types";
import { TrustStatusBadge } from "./TrustStatusBadge";
import { ConflictComparator } from "./ConflictComparator";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { ChevronDown, ChevronUp, AlertCircle, FileText, CheckCircle } from "lucide-react";

interface SpecificationTableProps {
  specifications: Record<string, Specification>;
  evidenceRecords: EvidenceRecord[];
  conflicts?: ConflictRecord[];
  onResolveConflict?: (field: string) => void;
  className?: string;
}

export function SpecificationTable({
  specifications,
  evidenceRecords,
  conflicts = [],
  onResolveConflict,
  className = "",
}: SpecificationTableProps) {
  const [filter, setFilter] = useState<string>("ALL");
  const [expandedField, setExpandedField] = useState<string | null>(null);

  const specList = Object.values(specifications);

  const filteredSpecs = specList.filter((spec) => {
    if (filter === "ALL") return true;
    if (filter === "VERIFIED") return spec.trust_status === "TRUSTED";
    if (filter === "INFERRED") return spec.trust_status === "UNVERIFIED" || spec.trust_status === "REVIEW_REQUIRED";
    if (filter === "CONFLICTED") return spec.trust_status === "CONFLICTED";
    if (filter === "UNKNOWN") return spec.trust_status === "MISSING" || spec.trust_status === "UNSUPPORTED";
    return true;
  });

  const toggleExpand = (field: string) => {
    setExpandedField(expandedField === field ? null : field);
  };

  const getFieldConflicts = (fieldName: string): ConflictRecord[] => {
    return conflicts.filter(
      (c) => (c.canonical_field || c.field || "").toLowerCase() === fieldName.toLowerCase()
    );
  };

  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden ${className}`}>
      {/* Table Header & Filters */}
      <div className="p-5 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gray-50/50">
        <div>
          <h3 className="font-sans font-bold text-gray-900 text-base">
            Technical Specifications & Physical Attributes
          </h3>
          <p className="text-xs text-gray-500 font-sans mt-0.5">
            Electromechanical parameters verified against canonical units
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 bg-gray-200/70 rounded-lg text-xs font-medium font-sans">
          {["ALL", "VERIFIED", "INFERRED", "CONFLICTED", "UNKNOWN"].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1 rounded-md transition-all ${
                filter === tab
                  ? "bg-white text-gray-900 shadow-sm font-semibold"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab === "ALL" ? "All Specs" : tab.charAt(0) + tab.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Table Body */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-gray-50 border-b border-gray-200 font-mono text-[11px] text-gray-500 uppercase tracking-wider">
            <tr>
              <th className="py-3 px-6 font-semibold">Attribute Name</th>
              <th className="py-3 px-6 font-semibold">Canonical Value</th>
              <th className="py-3 px-6 font-semibold">Trust Status</th>
              <th className="py-3 px-6 font-semibold">Evidence & Validation</th>
              <th className="py-3 px-6 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredSpecs.map((spec) => {
              const isExpanded = expandedField === spec.field;
              const fieldConflicts = getFieldConflicts(spec.field);
              const hasConflict = spec.trust_status === "CONFLICTED" || fieldConflicts.length > 0;
              const primaryConflict = fieldConflicts.length > 0 ? fieldConflicts[0] : undefined;

              return (
                <React.Fragment key={spec.field}>
                  <tr
                    onClick={() => toggleExpand(spec.field)}
                    className={`hover:bg-gray-50/80 cursor-pointer transition-colors ${
                      hasConflict ? "bg-rose-50/20" : ""
                    }`}
                  >
                    {/* Attribute Name */}
                    <td className="py-3.5 px-6 font-mono font-medium text-gray-900">
                      <div className="flex items-center gap-2">
                        <span>{spec.field}</span>
                        {hasConflict && (
                          <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
                        )}
                      </div>
                    </td>

                    {/* Value */}
                    <td className="py-3.5 px-6 font-mono">
                      {spec.canonical_value !== null && spec.canonical_value !== undefined ? (
                        <span className="font-bold text-gray-900 text-sm">
                          {spec.canonical_value} {spec.canonical_unit || ""}
                        </span>
                      ) : (
                        <span className="text-gray-400 font-normal italic">
                          {hasConflict ? "Unresolved Conflict (null)" : "Not Available"}
                        </span>
                      )}
                    </td>

                    {/* Trust Status */}
                    <td className="py-3.5 px-6">
                      <TrustStatusBadge status={spec.trust_status} size="sm" />
                    </td>

                    {/* Evidence & Validation */}
                    <td className="py-3.5 px-6 text-gray-600">
                      <div className="flex items-center gap-2">
                        {spec.evidence_sources && spec.evidence_sources.length > 0 ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                            <FileText className="w-3 h-3 text-gray-400" />
                            {spec.evidence_sources.length} source{spec.evidence_sources.length > 1 ? "s" : ""}
                          </span>
                        ) : (
                          <span className="text-gray-400 text-[11px]">—</span>
                        )}

                        {spec.validation_status === "PASS" && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-600">
                            <CheckCircle className="w-3 h-3" />
                            Physics Pass
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Expand Action */}
                    <td className="py-3.5 px-6 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleExpand(spec.field);
                        }}
                        className="p-1 rounded hover:bg-gray-200 text-gray-500 transition-colors"
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>

                  {/* Expanded Detail Panel */}
                  {isExpanded && (
                    <tr className="bg-gray-50/50">
                      <td colSpan={5} className="p-6">
                        {hasConflict ? (
                          <ConflictComparator
                            field={spec.field}
                            conflict={primaryConflict}
                            conflicts={fieldConflicts}
                            sources={primaryConflict?.sources}
                            description={primaryConflict?.description || spec.reason}
                            recommendedAction={
                              primaryConflict?.recommended_action ||
                              primaryConflict?.action_needed ||
                              spec.reason ||
                              "Inspect physical nameplate before catalog publishing."
                            }
                            onResolveClick={() =>
                              onResolveConflict && onResolveConflict(spec.field)
                            }
                          />
                        ) : (
                          <div className="space-y-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <span className="text-xs font-bold text-gray-800 font-sans">
                                  Validation & Trust Justification
                                </span>
                                <p className="text-xs text-gray-600 font-sans mt-0.5">
                                  {spec.reason || "Validated against physical catalog and electromechanical rules."}
                                </p>
                              </div>

                              {spec.validation_rule_ids && spec.validation_rule_ids.length > 0 && (
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  {spec.validation_rule_ids.map((rule) => (
                                    <span
                                      key={rule}
                                      className="text-[10px] font-mono bg-blue-50 text-blue-700 border border-blue-100 px-2 py-0.5 rounded"
                                    >
                                      {rule}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>

                            <EvidenceDrawer
                              attribute={spec.field}
                              records={evidenceRecords}
                            />
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
