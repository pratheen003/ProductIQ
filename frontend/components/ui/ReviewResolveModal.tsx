"use client";

import React, { useState } from "react";
import { ReviewItem, ConflictSource } from "@/lib/types";
import { api } from "@/lib/api";
import {
  X,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Database,
  Globe,
  HelpCircle,
  ShieldCheck,
  Edit3,
} from "lucide-react";

interface ReviewResolveModalProps {
  item: ReviewItem | null;
  isOpen: boolean;
  onClose: () => void;
  onResolvedSuccess: (updated: ReviewItem) => void;
}

export function ReviewResolveModal({
  item,
  isOpen,
  onClose,
  onResolvedSuccess,
}: ReviewResolveModalProps) {
  const [selectedSourceId, setSelectedSourceId] = useState<string>("");
  const [selectedValue, setSelectedValue] = useState<string>("");
  const [customValue, setCustomValue] = useState<string>("");
  const [note, setNote] = useState<string>("");
  const [reviewer, setReviewer] = useState<string>("Lead Application Engineer");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen || !item) return null;

  // Extract N sources
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    let finalVal: any = selectedValue;
    if (selectedSourceId === "custom") {
      finalVal = customValue;
    }

    if (!finalVal && finalVal !== 0) {
      setErrorMsg("Please select an authoritative source or enter a resolved value.");
      setIsSubmitting(false);
      return;
    }

    try {
      const res = await api.resolveReview(item.review_id, {
        selected_source: selectedSourceId || "manual",
        resolved_value: finalVal,
        resolution_note:
          note ||
          `Resolved to ${finalVal} by ${reviewer} based on engineering catalog audit.`,
        reviewer: reviewer,
      });

      if (res.success) {
        onResolvedSuccess({
          ...item,
          status: "RESOLVED",
          resolved_value: finalVal,
          resolution_note: note || `Resolved to ${finalVal} by ${reviewer}.`,
          resolved_by: reviewer,
        });
        onClose();
      } else {
        setErrorMsg(res.message || "Resolution failed.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit resolution.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl max-w-xl w-full overflow-hidden animate-in fade-in duration-200 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-gray-100 flex items-center justify-between bg-gray-50 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-brand-dark text-white flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-brand-muted" />
            </div>
            <div>
              <h3 className="font-sans font-bold text-gray-900 text-lg">
                Human Engineering Resolution
              </h3>
              <p className="text-xs text-gray-500 font-mono">
                {item.review_id} • {item.product_id}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content & Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Issue Summary */}
          <div className="p-3.5 rounded-lg bg-gray-50 border border-gray-200 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-800 font-sans">
                Target: {item.target_name} ({item.target_type})
              </span>
              <span className="text-[10px] font-mono font-bold bg-rose-100 text-rose-800 px-2 py-0.5 rounded">
                {item.severity}
              </span>
            </div>
            <p className="text-xs text-gray-600 font-sans">{item.description}</p>
          </div>

          {/* N-Source Choices */}
          {sources.length > 0 && (
            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-800 font-sans block">
                Select Authoritative Source or Specify Custom Value:
              </label>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {sources.map((src, idx) => {
                  const sId = src.source_id || `src_${idx}`;
                  const isChecked = selectedSourceId === sId;
                  const displayVal =
                    src.value !== null && src.value !== undefined
                      ? `${src.value} ${src.unit || ""}`.trim()
                      : src.raw_value || "null";

                  return (
                    <label
                      key={idx}
                      className={`p-3.5 rounded-xl border-2 cursor-pointer flex flex-col justify-between transition-all ${
                        isChecked
                          ? "border-brand-accent bg-brand-accent/5 shadow-subtle"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 font-mono text-xs font-semibold text-gray-800 truncate">
                          {getSourceIcon(src.source_type)}
                          <span className="truncate">
                            {src.source_name || `${(src.source_type || "source").toUpperCase()} Source`}
                          </span>
                        </div>
                        <input
                          type="radio"
                          name="source_option"
                          value={sId}
                          checked={isChecked}
                          onChange={() => {
                            setSelectedSourceId(sId);
                            setSelectedValue(String(src.value ?? src.raw_value ?? ""));
                          }}
                          className="accent-brand-accent ml-2"
                        />
                      </div>
                      <div className="mt-2 text-xl font-mono font-bold text-gray-900">
                        {displayVal}
                      </div>
                      {src.location && (
                        <div className="mt-2 text-[10px] text-gray-500 font-mono truncate">
                          {src.location}
                        </div>
                      )}
                    </label>
                  );
                })}

                {/* Custom Value Option */}
                <label
                  className={`p-3.5 rounded-xl border-2 cursor-pointer flex flex-col justify-between transition-all ${
                    selectedSourceId === "custom"
                      ? "border-brand-accent bg-brand-accent/5 shadow-subtle"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 font-mono text-xs font-semibold text-gray-800">
                      <Edit3 className="w-4 h-4 text-purple-600" />
                      <span>Custom Nameplate Value</span>
                    </div>
                    <input
                      type="radio"
                      name="source_option"
                      value="custom"
                      checked={selectedSourceId === "custom"}
                      onChange={() => setSelectedSourceId("custom")}
                      className="accent-brand-accent"
                    />
                  </div>
                  <div className="mt-2">
                    <input
                      type="text"
                      placeholder="Enter verified value..."
                      value={customValue}
                      onChange={(e) => {
                        setCustomValue(e.target.value);
                        setSelectedSourceId("custom");
                      }}
                      className="w-full text-xs font-mono p-1.5 border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-brand-accent"
                    />
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* Justification Note */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-800 font-sans block">
              Engineering Justification Note:
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Verified against physical nameplate catalog; CSV value represented locked rotor or test bench current."
              rows={2}
              className="w-full text-xs font-sans p-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-accent focus:border-transparent"
            />
          </div>

          {/* Reviewer Name */}
          <div className="flex items-center justify-between gap-4 text-xs font-sans">
            <span className="text-gray-500">Reviewer:</span>
            <input
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              className="font-mono text-xs text-right border border-gray-200 rounded px-2.5 py-1 text-gray-800 focus:outline-none focus:ring-1 focus:ring-brand-accent"
            />
          </div>

          {/* Actions */}
          <div className="pt-4 border-t border-gray-100 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-gray-600 hover:bg-gray-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-5 py-2 rounded-lg text-xs font-semibold bg-brand-accent hover:bg-brand-accentHover text-white shadow-sm transition-all disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{isSubmitting ? "Persisting..." : "Confirm Resolution"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
