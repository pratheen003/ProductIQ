"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ProductSummary } from "@/lib/types";
import { TrustStatusBadge } from "@/components/ui/TrustStatusBadge";
import { PublishabilityBadge } from "@/components/ui/PublishabilityBadge";
import { Search, Filter, ArrowUpDown, ArrowRight, Database, AlertTriangle } from "lucide-react";

export default function ProductsPage() {
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<"power" | "score" | "id">("power");
  const [sortAsc, setSortAsc] = useState<boolean>(true);

  useEffect(() => {
    async function loadProducts() {
      try {
        setLoading(true);
        const data = await api.getProducts();
        setProducts(data);
      } catch (err) {
        console.error("Products loading error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadProducts();
  }, []);

  const filtered = products
    .filter((p) => {
      const matchSearch =
        search === "" ||
        p.product_id.toLowerCase().includes(search.toLowerCase()) ||
        p.model.toLowerCase().includes(search.toLowerCase()) ||
        (p.rated_power_kw && `${p.rated_power_kw}kw`.includes(search.toLowerCase()));

      const matchStatus =
        statusFilter === "ALL" ||
        (statusFilter === "CONFLICTED" && p.overall_trust_status === "CONFLICTED") ||
        (statusFilter === "TRUSTED" && p.overall_trust_status === "TRUSTED") ||
        (statusFilter === "REVIEW_REQUIRED" && p.overall_publishability === "REVIEW_REQUIRED");

      return matchSearch && matchStatus;
    })
    .sort((a, b) => {
      let cmp = 0;
      if (sortBy === "power") {
        cmp = (a.rated_power_kw || 0) - (b.rated_power_kw || 0);
      } else if (sortBy === "score") {
        cmp = a.trust_score - b.trust_score;
      } else {
        cmp = a.product_id.localeCompare(b.product_id);
      }
      return sortAsc ? cmp : -cmp;
    });

  const toggleSort = (field: "power" | "score" | "id") => {
    if (sortBy === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortBy(field);
      setSortAsc(true);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold font-sans text-gray-900 tracking-tight">
            Industrial Equipment Catalog
          </h2>
          <p className="text-xs text-gray-500 font-sans mt-0.5">
            Normalized motor specifications across 12 WEG W22 Severe Process products
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-gray-500 bg-white px-3 py-1.5 rounded-lg border border-gray-200 shadow-subtle">
          <Database className="w-4 h-4 text-brand-accent" />
          <span>Total Records: {products.length} Motors</span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by SKU (e.g. 1.1kW, 4P, 15kW, W22)..."
            className="w-full pl-10 pr-4 py-2 text-xs font-mono rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-accent focus:border-transparent"
          />
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-gray-100 rounded-lg text-xs font-sans">
          {[
            { id: "ALL", label: "All Motors" },
            { id: "CONFLICTED", label: "Conflicted (12)" },
            { id: "REVIEW_REQUIRED", label: "Review Required" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                statusFilter === tab.id
                  ? "bg-white text-gray-900 shadow-sm font-semibold"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Products Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-gray-400 font-mono animate-pulse">
            Loading products from FastAPI bridge...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-xs text-gray-500 font-sans">
            No products matched your search criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 border-b border-gray-100 font-mono text-[11px] text-gray-500 uppercase tracking-wider">
                <tr>
                  <th
                    className="py-3 px-6 font-semibold cursor-pointer hover:text-gray-900"
                    onClick={() => toggleSort("id")}
                  >
                    <div className="flex items-center gap-1">
                      <span>Product SKU</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th
                    className="py-3 px-6 font-semibold cursor-pointer hover:text-gray-900"
                    onClick={() => toggleSort("power")}
                  >
                    <div className="flex items-center gap-1">
                      <span>Power</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="py-3 px-6 font-semibold">Speed / Poles</th>
                  <th className="py-3 px-6 font-semibold">Frame Size</th>
                  <th
                    className="py-3 px-6 font-semibold cursor-pointer hover:text-gray-900"
                    onClick={() => toggleSort("score")}
                  >
                    <div className="flex items-center gap-1">
                      <span>Trust Score</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="py-3 px-6 font-semibold">Quality Status</th>
                  <th className="py-3 px-6 font-semibold">Publishability</th>
                  <th className="py-3 px-6 font-semibold">Reviews</th>
                  <th className="py-3 px-6 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((p) => (
                  <tr
                    key={p.product_id}
                    className="hover:bg-gray-50/80 transition-colors group cursor-pointer"
                  >
                    {/* SKU */}
                    <td className="py-4 px-6 font-mono font-bold text-gray-900">
                      <Link
                        href={`/products/${p.product_id}`}
                        className="hover:text-brand-accent transition-colors flex items-center gap-2"
                      >
                        <span>{p.product_id}</span>
                        {p.product_id === "PIQ-W22SP-4P-1.1" && (
                          <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-rose-100 text-rose-800 rounded">
                            Demo Hard-Gate
                          </span>
                        )}
                      </Link>
                    </td>

                    {/* Power */}
                    <td className="py-4 px-6 font-mono font-bold text-gray-900 text-sm">
                      {p.rated_power_kw ? `${p.rated_power_kw} kW` : "—"}
                    </td>

                    {/* Speed & Poles */}
                    <td className="py-4 px-6 font-mono text-gray-600">
                      {p.rated_speed_rpm ? `${p.rated_speed_rpm} RPM` : "—"}{" "}
                      <span className="text-gray-400">({p.poles ? `${p.poles}P` : "—"})</span>
                    </td>

                    {/* Frame Size */}
                    <td className="py-4 px-6 font-mono text-gray-700">
                      {p.frame_size || "—"}
                    </td>

                    {/* Score */}
                    <td className="py-4 px-6 font-mono font-bold">
                      <span className="px-2.5 py-1 bg-gray-100 rounded text-gray-900">
                        {(p.trust_score * 100).toFixed(1)}
                      </span>
                    </td>

                    {/* Quality Status */}
                    <td className="py-4 px-6">
                      <TrustStatusBadge status={p.overall_trust_status} size="sm" />
                    </td>

                    {/* Publishability */}
                    <td className="py-4 px-6">
                      <PublishabilityBadge status={p.overall_publishability} />
                    </td>

                    {/* Review Count */}
                    <td className="py-4 px-6 font-mono font-semibold text-rose-600">
                      {p.review_items_count} items
                    </td>

                    {/* Action */}
                    <td className="py-4 px-6 text-right">
                      <Link
                        href={`/products/${p.product_id}`}
                        className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-brand-accent hover:text-white text-gray-700 transition-all inline-flex items-center gap-1"
                      >
                        <span>Inspect Specs</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
