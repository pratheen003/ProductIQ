"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Sparkles,
  ShieldCheck,
  RefreshCw,
  Layers,
  FileText,
  Tag,
  Cpu,
} from "lucide-react";
import { api } from "@/lib/api";
import { CatalogProductDTO, CatalogTrustStatusType } from "@/lib/types";

export default function CatalogProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const rowId = parseInt(params?.id as string, 10);

  const [product, setProduct] = useState<CatalogProductDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [enriching, setEnriching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProduct = async () => {
    if (isNaN(rowId)) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCatalogProductDetail(rowId);
      setProduct(data);
    } catch (err: any) {
      setError(err.message || `Failed to load product row #${rowId}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLiveReEnrich = async () => {
    setEnriching(true);
    try {
      const refreshed = await api.enrichCatalogRow(rowId);
      setProduct(refreshed);
    } catch (err: any) {
      alert(`Enrichment error: ${err.message}`);
    } finally {
      setEnriching(false);
    }
  };

  useEffect(() => {
    loadProduct();
  }, [rowId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-brand-accent animate-spin" />
          <p className="text-sm text-slate-500 font-medium">Loading catalog item #{rowId}...</p>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="p-8 space-y-4">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Products
        </button>
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-rose-700">
          <h3 className="font-semibold text-lg mb-2">Item Not Found</h3>
          <p className="text-sm">{error || `Catalog row #${rowId} could not be loaded.`}</p>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status: CatalogTrustStatusType) => {
    switch (status) {
      case "Verified":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-4 h-4" />
            Verified (100% Match)
          </span>
        );
      case "Inferred":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
            <Sparkles className="w-4 h-4" />
            Inferred (Rule Normalized)
          </span>
        );
      case "Conflicted":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            Conflicted (Multi-Source Disagreement)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
            <HelpCircle className="w-4 h-4 text-slate-400" />
            Unknown (Suppressed to Prevent Hallucination)
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Navigation Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <button
            onClick={() => router.push("/catalog/products")}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to 1,000 Products Explorer
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-slate-900 font-mono">
              {product.mfg_part_num}
            </h1>
            <span className="text-xs px-2 py-0.5 rounded font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
              Row #{product.row_id}
            </span>
            {getStatusBadge(product.overall_trust_status)}
          </div>
          <p className="text-slate-600 text-sm mt-1 max-w-2xl">
            {product.part_desc || "No description provided in raw dataset."}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleLiveReEnrich}
            disabled={enriching}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-accent text-white rounded-lg text-sm font-semibold shadow hover:bg-brand-accent/90 disabled:opacity-50 transition"
          >
            <RefreshCw className={`w-4 h-4 ${enriching ? "animate-spin" : ""}`} />
            <span>{enriching ? "Re-processing..." : "Re-Enrich Live"}</span>
          </button>
        </div>
      </div>

      {/* Brand Conflict Banner (If Conflicted) */}
      {product.has_conflicts && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-amber-100 text-amber-800 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-amber-600" />
            </div>
            <div className="flex-1 space-y-2">
              <h3 className="font-bold text-amber-900 text-base">
                Cross-Column Brand Conflict Detected
              </h3>
              <p className="text-xs text-amber-800 leading-relaxed">
                Input asserts conflicting brand identities across non-placeholder columns. In accordance with the project&apos;s no-silent-winner discipline, ProductIQ suppresses the brand value rather than arbitrarily guessing.
              </p>
              <div className="pt-2 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="p-2.5 bg-white rounded-lg border border-amber-200">
                  <span className="text-slate-500 font-medium block">Part_Manuf:</span>
                  <span className="font-mono font-semibold text-slate-900">{product.raw_input.part_manuf || "None"}</span>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-amber-200">
                  <span className="text-slate-500 font-medium block">E1_Brand:</span>
                  <span className="font-mono font-semibold text-slate-900">{product.raw_input.e1_brand || "None"}</span>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-amber-200">
                  <span className="text-slate-500 font-medium block">Unilog_Brand:</span>
                  <span className="font-mono font-semibold text-slate-900">{product.raw_input.unilog_brand || "None"}</span>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-amber-200">
                  <span className="text-slate-500 font-medium block">DIB_Brand:</span>
                  <span className="font-mono font-semibold text-slate-900">{product.raw_input.dib_brand || "None"}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Raw Input vs Enriched Delivery Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Raw Ingestion Signals */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-500" />
              Raw Input Record (Unilog CSV)
            </h3>
            <span className="text-xs text-slate-400 font-mono">Row #{product.row_id}</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">Mfg_Part_Num:</span>
              <span className="font-mono font-bold text-slate-900">{product.raw_input.mfg_part_num}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">Part_Manuf:</span>
              <span className="font-mono text-slate-800">{product.raw_input.part_manuf || <span className="text-slate-400 italic">None</span>}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">E1_Brand:</span>
              <span className="font-mono text-slate-800">{product.raw_input.e1_brand || <span className="text-slate-400 italic">None</span>}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">Unilog_Brand:</span>
              <span className="font-mono text-slate-800">{product.raw_input.unilog_brand || <span className="text-slate-400 italic">None</span>}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">DIB_Brand:</span>
              <span className="font-mono text-slate-800">{product.raw_input.dib_brand || <span className="text-slate-400 italic">None</span>}</span>
            </div>
            <div className="pt-2">
              <span className="text-slate-500 font-medium block mb-1">Part_Desc:</span>
              <p className="p-2.5 bg-slate-50 rounded-lg text-slate-700 font-mono text-xs leading-relaxed border border-slate-100">
                {product.raw_input.part_desc || "None"}
              </p>
            </div>
          </div>
        </div>

        {/* Enriched Delivery Columns */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-brand-accent" />
              Standardized Delivery Output
            </h3>
            <span className="text-xs text-brand-accent font-semibold">Scoped Canonical Fields</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">MANUFACTURER_NAME:</span>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900">
                  {product.manufacturer_name.value || <span className="text-slate-400 italic">Unknown</span>}
                </span>
                {getStatusBadge(product.manufacturer_name.status)}
              </div>
            </div>

            <div className="flex items-center justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">BRAND_NAME:</span>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900">
                  {product.brand_name.value || <span className="text-slate-400 italic">Unknown</span>}
                </span>
                {getStatusBadge(product.brand_name.status)}
              </div>
            </div>

            <div className="flex items-center justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">MANUFACTURER_PART_NUMBER:</span>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-slate-900">
                  {product.manufacturer_part_number.value || <span className="text-slate-400 italic">Unknown</span>}
                </span>
                {getStatusBadge(product.manufacturer_part_number.status)}
              </div>
            </div>

            <div className="flex items-center justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">Product Name:</span>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900">
                  {product.product_name.value || <span className="text-slate-400 italic">Unknown</span>}
                </span>
                {getStatusBadge(product.product_name.status)}
              </div>
            </div>

            <div className="flex items-center justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-medium">Classpath:</span>
              <div className="flex items-center gap-2 max-w-xs truncate">
                <span className="font-mono text-slate-700 truncate" title={product.classpath.value || ""}>
                  {product.classpath.value || <span className="text-slate-400 italic">Unknown</span>}
                </span>
              </div>
            </div>

            <div className="pt-2">
              <span className="text-slate-500 font-medium block mb-1">Synthesized SHORT_DESCRIPTION:</span>
              <p className="p-2.5 bg-slate-50 rounded-lg text-slate-900 font-semibold text-xs border border-slate-100">
                {product.short_desc.value || <span className="text-slate-400 italic font-normal">Suppressed (Incomplete verified components)</span>}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Normalized Technical Attributes Table */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wider flex items-center gap-2">
            <Tag className="w-4 h-4 text-slate-500" />
            Extracted &amp; Normalized Attributes (Triples)
          </h3>
          <span className="text-xs text-slate-500 font-medium">
            {product.attributes.length} Physical / Dimensional Attributes
          </span>
        </div>

        {product.attributes.length === 0 ? (
          <div className="p-6 text-center text-slate-400 text-xs italic">
            No recognizable dimensional, electrical, or acoustic attributes found in description text.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Attribute Label</th>
                  <th className="py-2.5 px-3">Normalized Value</th>
                  <th className="py-2.5 px-3">Canonical UOM</th>
                  <th className="py-2.5 px-3">Raw Substring</th>
                  <th className="py-2.5 px-3">Trust Tier</th>
                  <th className="py-2.5 px-3">Confidence</th>
                  <th className="py-2.5 px-3">Reasoning / Formula</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {product.attributes.map((attr, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/60">
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{attr.label}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-slate-800">{attr.value}</td>
                    <td className="py-2.5 px-3 font-mono text-brand-accent font-bold">{attr.uom || "—"}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-500">{attr.raw_value}{attr.raw_uom || ""}</td>
                    <td className="py-2.5 px-3">{getStatusBadge(attr.status)}</td>
                    <td className="py-2.5 px-3 font-mono font-semibold">{(attr.confidence * 100).toFixed(0)}%</td>
                    <td className="py-2.5 px-3 text-slate-500 max-w-xs truncate" title={attr.reason}>
                      {attr.reason}
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
