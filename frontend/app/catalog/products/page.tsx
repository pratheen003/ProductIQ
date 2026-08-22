"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Table,
  Search,
  Filter,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import { CatalogProductSummaryDTO, CatalogProductsListResponse } from "@/lib/types";

export default function CatalogProductsPage() {
  const [data, setData] = useState<CatalogProductsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [conflictsOnly, setConflictsOnly] = useState<boolean | undefined>(undefined);

  const loadProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCatalogProducts({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
        has_conflicts: conflictsOnly,
      });
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load catalog products");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, [page, pageSize, statusFilter, conflictsOnly]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadProducts();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Verified":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Verified
          </span>
        );
      case "Inferred":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Sparkles className="w-3.5 h-3.5" />
            Inferred
          </span>
        );
      case "Conflicted":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            Conflicted
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            Unknown
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 text-xs font-bold font-mono uppercase bg-brand-accent/10 text-brand-accent rounded">
              Unilog Dataset
            </span>
            <span className="text-xs text-slate-500">1,000 Total Rows</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Catalog Items Explorer
          </h1>
          <p className="text-slate-600 mt-1">
            Browse enriched catalog items, inspect normalized attributes, and review conflict flags.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
          {/* Search Form */}
          <form onSubmit={handleSearchSubmit} className="relative flex-1 w-full max-w-md">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search part #, description, brand..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-accent/20 focus:border-brand-accent"
            />
          </form>

          {/* Quick Filters */}
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-xs font-medium rounded-lg border border-slate-200 bg-slate-50 text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-accent/20"
            >
              <option value="">All Trust Statuses</option>
              <option value="Verified">Verified Only</option>
              <option value="Inferred">Inferred Only</option>
              <option value="Conflicted">Conflicted Only</option>
              <option value="Unknown">Unknown Only</option>
            </select>

            <button
              onClick={() => {
                setConflictsOnly(conflictsOnly ? undefined : true);
                setPage(1);
              }}
              className={`px-3 py-2 text-xs font-semibold rounded-lg border transition ${
                conflictsOnly
                  ? "bg-amber-100 border-amber-300 text-amber-800"
                  : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              {conflictsOnly ? "Showing Conflicts" : "Filter Conflicts"}
            </button>

            <button
              onClick={loadProducts}
              className="p-2 text-slate-500 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Products Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-6 h-6 text-brand-accent animate-spin" />
            <p className="text-sm text-slate-500">Loading catalog items...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-600 text-sm">{error}</div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No catalog items found matching your filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-600 uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="py-3.5 px-4 w-16">Row</th>
                  <th className="py-3.5 px-4">Mfg Part #</th>
                  <th className="py-3.5 px-4">Description</th>
                  <th className="py-3.5 px-4">Manufacturer</th>
                  <th className="py-3.5 px-4">Brand</th>
                  <th className="py-3.5 px-4">Trust Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((item) => (
                  <tr key={item.row_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-500 font-bold">
                      #{item.row_id}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-slate-900">
                      {item.mfg_part_num}
                    </td>
                    <td className="py-3.5 px-4 max-w-xs truncate text-xs text-slate-600" title={item.part_desc || ""}>
                      {item.part_desc || "—"}
                    </td>
                    <td className="py-3.5 px-4 text-xs font-medium text-slate-800">
                      {item.manufacturer || <span className="text-slate-400 italic">Unknown</span>}
                    </td>
                    <td className="py-3.5 px-4 text-xs font-medium text-slate-800">
                      {item.brand || <span className="text-slate-400 italic">Unknown</span>}
                    </td>
                    <td className="py-3.5 px-4">
                      {getStatusBadge(item.overall_status)}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        href={`/catalog/products/${item.row_id}`}
                        className="inline-flex items-center px-2.5 py-1 text-xs font-semibold text-brand-accent hover:text-brand-accent/80 hover:bg-brand-accent/10 rounded transition"
                      >
                        Inspect →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {data && data.total > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50/50">
            <div className="text-xs text-slate-500">
              Showing <span className="font-semibold text-slate-800">{(page - 1) * pageSize + 1}</span> to{" "}
              <span className="font-semibold text-slate-800">
                {Math.min(page * pageSize, data.total)}
              </span>{" "}
              of <span className="font-semibold text-slate-800">{data.total}</span> items
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page === 1}
                className="p-2 border border-slate-200 rounded-lg bg-white text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs font-semibold text-slate-700 px-2">
                Page {page} of {data.total_pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(p + 1, data.total_pages))}
                disabled={page >= data.total_pages}
                className="p-2 border border-slate-200 rounded-lg bg-white text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
