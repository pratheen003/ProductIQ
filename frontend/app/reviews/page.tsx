"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ReviewItem } from "@/lib/types";
import { ReviewItemCard } from "@/components/ui/ReviewItemCard";
import { ReviewResolveModal } from "@/components/ui/ReviewResolveModal";
import {
  ShieldAlert,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ArrowUpDown,
} from "lucide-react";

export default function ReviewQueuePage() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [issueTypeFilter, setIssueTypeFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  // Modal
  const [selectedItem, setSelectedItem] = useState<ReviewItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  useEffect(() => {
    async function loadReviews() {
      try {
        setLoading(true);
        const data = await api.getReviews();
        setReviews(data);
      } catch (err) {
        console.error("Reviews load error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadReviews();
  }, []);

  const handleOpenResolve = (item: ReviewItem) => {
    setSelectedItem(item);
    setIsModalOpen(true);
  };

  const handleResolvedSuccess = (updatedItem: ReviewItem) => {
    setReviews((prev) =>
      prev.map((r) => (r.review_id === updatedItem.review_id ? updatedItem : r))
    );
  };

  const filtered = reviews.filter((item) => {
    const matchSearch =
      search === "" ||
      item.review_id.toLowerCase().includes(search.toLowerCase()) ||
      item.product_id.toLowerCase().includes(search.toLowerCase()) ||
      item.target_name.toLowerCase().includes(search.toLowerCase()) ||
      item.description.toLowerCase().includes(search.toLowerCase());

    const matchSeverity =
      severityFilter === "ALL" || item.severity.toUpperCase() === severityFilter.toUpperCase();

    const matchIssue =
      issueTypeFilter === "ALL" || item.issue_type.toUpperCase() === issueTypeFilter.toUpperCase();

    const matchStatus =
      statusFilter === "ALL" || item.status.toUpperCase() === statusFilter.toUpperCase();

    return matchSearch && matchSeverity && matchIssue && matchStatus;
  });

  const conflictsCount = reviews.filter((r) => r.issue_type === "CONFLICT").length;
  const warningsCount = reviews.filter((r) => r.issue_type === "WARNING").length;
  const resolvedCount = reviews.filter((r) => r.status === "RESOLVED").length;

  return (
    <div className="space-y-8">
      {/* Header Bar (Reference Design Page 4) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-gray-200 shadow-card">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold font-sans text-gray-900 tracking-tight">
              Human Review & Resolution Queue
            </h2>
            <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-rose-100 text-rose-800 border border-rose-200">
              {reviews.length - resolvedCount} Open / {reviews.length} Total
            </span>
          </div>
          <p className="text-xs text-gray-500 font-sans mt-1">
            Resolve multi-source data conflicts and verify engineering tolerances before catalog publication
          </p>
        </div>

        {resolvedCount > 0 && (
          <div className="flex items-center gap-2 text-xs font-mono text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200">
            <CheckCircle2 className="w-4 h-4" />
            <span>{resolvedCount} items resolved in session</span>
          </div>
        )}
      </div>

      {/* Filter Tabs & Search Bar (Reference Design Page 4) */}
      <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 bg-gray-100 rounded-lg text-xs font-sans">
          {[
            { id: "ALL", label: `All Flags (${reviews.length})` },
            { id: "CONFLICT", label: `Conflicts (${conflictsCount})` },
            { id: "WARNING", label: `Warnings (${warningsCount})` },
            { id: "RESOLVED", label: `Resolved (${resolvedCount})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                if (tab.id === "RESOLVED") {
                  setStatusFilter("RESOLVED");
                  setIssueTypeFilter("ALL");
                } else if (tab.id === "ALL") {
                  setStatusFilter("ALL");
                  setIssueTypeFilter("ALL");
                } else {
                  setStatusFilter("ALL");
                  setIssueTypeFilter(tab.id);
                }
              }}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                (tab.id === "RESOLVED" && statusFilter === "RESOLVED") ||
                (tab.id !== "RESOLVED" && statusFilter !== "RESOLVED" && issueTypeFilter === tab.id) ||
                (tab.id === "ALL" && issueTypeFilter === "ALL" && statusFilter === "ALL")
                  ? "bg-white text-gray-900 shadow-sm font-semibold"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by SKU, field name, or review ID..."
            className="w-full pl-10 pr-4 py-2 text-xs font-mono rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-accent focus:border-transparent"
          />
        </div>
      </div>

      {/* Review Items List */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-12 text-center text-xs text-gray-400 font-mono animate-pulse">
            Loading review queue items from FastAPI...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-xs text-gray-500 font-sans bg-white rounded-2xl border border-gray-200">
            No review items match your active filters.
          </div>
        ) : (
          filtered.map((item) => (
            <ReviewItemCard
              key={item.review_id}
              item={item}
              onResolve={handleOpenResolve}
            />
          ))
        )}
      </div>

      {/* Resolution Modal */}
      <ReviewResolveModal
        item={selectedItem}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onResolvedSuccess={handleResolvedSuccess}
      />
    </div>
  );
}
