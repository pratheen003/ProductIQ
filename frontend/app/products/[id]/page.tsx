"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { ProductDetail, ReviewItem } from "@/lib/types";
import { TrustScoreGauge } from "@/components/ui/TrustScoreGauge";
import { TrustStatusBadge } from "@/components/ui/TrustStatusBadge";
import { PublishabilityBadge } from "@/components/ui/PublishabilityBadge";
import { SpecificationTable } from "@/components/ui/SpecificationTable";
import { ConflictComparator } from "@/components/ui/ConflictComparator";
import { ReviewResolveModal } from "@/components/ui/ReviewResolveModal";
import {
  ArrowLeft,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Sparkles,
  Layers,
  CheckCircle2,
  ExternalLink,
  Tag,
  Cpu,
} from "lucide-react";

export default function ProductDetailPage() {
  const params = useParams();
  const productId = params?.id as string;

  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Review modal state
  const [selectedReviewItem, setSelectedReviewItem] = useState<ReviewItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  useEffect(() => {
    if (!productId) return;

    async function loadProduct() {
      try {
        setLoading(true);
        const data = await api.getProductDetail(productId);
        setProduct(data);
      } catch (err: any) {
        console.error("Product detail error:", err);
        setError(err.message || "Failed to load product intelligence.");
      } finally {
        setLoading(false);
      }
    }

    loadProduct();
  }, [productId]);

  const handleOpenResolve = (field: string) => {
    if (!product) return;
    const item = product.review_queue.find(
      (r) => r.target_name.toLowerCase() === field.toLowerCase()
    );
    if (item) {
      setSelectedReviewItem(item);
      setIsModalOpen(true);
    }
  };

  const handleResolvedSuccess = (updatedItem: ReviewItem) => {
    if (!product) return;
    setProduct({
      ...product,
      review_queue: product.review_queue.map((r) =>
        r.review_id === updatedItem.review_id ? updatedItem : r
      ),
    });
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/5" />
        <div className="h-32 bg-gray-200 rounded-2xl" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-64 bg-gray-200 rounded-xl" />
          <div className="h-64 bg-gray-200 rounded-xl col-span-2" />
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="p-8 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 space-y-4">
        <h3 className="font-bold text-lg font-sans">Product Intelligence Not Found</h3>
        <p className="text-xs">{error || `Product '${productId}' could not be loaded.`}</p>
        <Link
          href="/products"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-rose-600 text-white"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Catalog</span>
        </Link>
      </div>
    );
  }

  const criticalFields = ["rated_voltage", "rated_power", "rated_speed", "rated_current"];

  return (
    <div className="space-y-8">
      {/* Breadcrumbs & Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-sans text-gray-500">
          <Link href="/products" className="hover:text-gray-900 transition-colors">
            Products
          </Link>
          <span>/</span>
          <span className="font-mono font-bold text-gray-900">{product.product_id}</span>
        </div>

        <Link
          href="/products"
          className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Catalog</span>
        </Link>
      </div>

      {/* Product Hero Banner */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-gray-200 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-brand-dark text-white">
              {product.product_id}
            </span>
            <span className="text-xs text-gray-500 font-sans">
              Manufacturer: <strong className="text-gray-800">{product.manufacturer}</strong>
            </span>
            <span className="text-xs text-gray-400">•</span>
            <span className="text-xs text-gray-500 font-sans">
              Category: <strong className="text-gray-800">{product.category}</strong>
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-bold font-sans text-gray-900 tracking-tight">
            {product.model}
          </h2>

          <p className="text-xs text-gray-600 font-sans max-w-2xl leading-relaxed">
            {product.commercial_summary ||
              "High-efficiency industrial cast iron induction motor engineered for severe process environments."}
          </p>
        </div>

        {/* Status Badges */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 shrink-0">
          <div className="flex flex-col items-end gap-1.5">
            <TrustStatusBadge status={product.overall_trust_status} size="lg" />
            <PublishabilityBadge status={product.overall_publishability} />
          </div>
        </div>
      </div>

      {/* Trust Gauge & Critical Specs Cards (Reference Design Page 2) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Data Trust Score Gauge */}
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-card flex flex-col justify-between">
          <div className="flex items-center justify-between pb-4 border-b border-gray-100">
            <div>
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-gray-500">
                Data Trust Score
              </span>
              <p className="text-[11px] text-gray-400 font-sans">Deterministic Physics Metric</p>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-gray-100 text-gray-700 rounded">
              FORMULA v5.0
            </span>
          </div>

          <div className="py-4 flex justify-center">
            <TrustScoreGauge
              score={product.trust_score}
              breakdown={product.trust_score_breakdown}
              size="lg"
            />
          </div>

          <div className="pt-3 border-t border-gray-100 text-[11px] font-mono text-gray-500 leading-tight">
            <span className="font-semibold text-gray-700">Formula: </span>
            <span className="text-[10px] text-gray-600 block mt-0.5 break-all">
              {product.trust_score_formula || "TrustScore = clamp(0.35*C + 0.35*V + 0.3*D - Penalty)"}
            </span>
          </div>
        </div>

        {/* Card 2 & 3: Critical Specifications Grid */}
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-card lg:col-span-2 flex flex-col justify-between">
          <div className="flex items-center justify-between pb-4 border-b border-gray-100">
            <div>
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-gray-500">
                Critical Specifications
              </span>
              <p className="text-[11px] text-gray-400 font-sans">Key operational and electrical parameters</p>
            </div>
            <span className="text-xs font-mono text-gray-500">
              {product.publishable_attributes.length} Publishable / {product.restricted_attributes.length} Restricted
            </span>
          </div>

          {/* 4 Cards for Top Specs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 py-4">
            {criticalFields.map((fieldKey) => {
              const spec = product.specifications[fieldKey];
              if (!spec) return null;

              const isConflicted = spec.trust_status === "CONFLICTED";

              return (
                <div
                  key={fieldKey}
                  className={`p-3.5 rounded-xl border flex flex-col justify-between ${
                    isConflicted
                      ? "border-rose-300 bg-rose-50/40"
                      : "border-gray-200 bg-gray-50/50"
                  }`}
                >
                  <span className="text-[11px] font-mono font-semibold text-gray-500 uppercase truncate">
                    {fieldKey.replace("rated_", "").replace("_", " ")}
                  </span>

                  <div className="my-2">
                    {spec.canonical_value !== null ? (
                      <span className="font-mono font-bold text-gray-900 text-lg">
                        {spec.canonical_value} <span className="text-xs text-gray-500">{spec.canonical_unit}</span>
                      </span>
                    ) : (
                      <span className="font-mono text-rose-600 font-semibold text-xs">
                        Conflicted (null)
                      </span>
                    )}
                  </div>

                  <TrustStatusBadge status={spec.trust_status} size="sm" />
                </div>
              );
            })}
          </div>

          <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500 font-sans">
            <span>Review Items for this Motor: <strong className="text-rose-600 font-mono">{product.review_queue.length}</strong></span>
            {product.unresolved_conflicts.length > 0 && (
              <span className="text-rose-600 font-semibold flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>{product.unresolved_conflicts.length} Unresolved Conflicts</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Prominent Demo Conflict Comparator if Conflicted */}
      {product.unresolved_conflicts.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-sans font-bold text-gray-900 text-lg">
              Primary Data Conflict Spotlight
            </h3>
            <span className="text-xs font-mono text-rose-600 bg-rose-50 px-2.5 py-1 rounded-full border border-rose-200">
              Zero Arbitrary Winner Selected
            </span>
          </div>

          {product.unresolved_conflicts.map((conf, idx) => (
            <ConflictComparator
              key={idx}
              field={conf.canonical_field || conf.field || "rated_current"}
              conflict={conf}
              sources={conf.sources}
              description={conf.description}
              recommendedAction={
                conf.recommended_action ||
                conf.action_needed ||
                "Verify manufacturer physical nameplate or official dimension drawing before catalog publishing."
              }
              onResolveClick={() =>
                handleOpenResolve(conf.canonical_field || conf.field || "rated_current")
              }
            />
          ))}
        </div>
      )}

      {/* Full Specifications Table */}
      <SpecificationTable
        specifications={product.specifications}
        evidenceRecords={product.evidence_records}
        conflicts={product.unresolved_conflicts}
        onResolveConflict={(field) => handleOpenResolve(field)}
      />

      {/* Grounded AI Claims & Technical Synthesis */}
      <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-card space-y-5">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-brand-accent" />
            <div>
              <h3 className="font-sans font-bold text-gray-900 text-base">
                Grounded AI Claims & Synthesis
              </h3>
              <p className="text-xs text-gray-500 font-sans">
                Validated against underlying electromechanical attributes & source evidence
              </p>
            </div>
          </div>
          <span className="text-xs font-mono bg-purple-50 text-purple-700 px-2.5 py-1 rounded-full border border-purple-200">
            {product.claims.length} Claims Evaluated
          </span>
        </div>

        {/* Claims List */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {product.claims.map((claim, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl border border-gray-200 bg-gray-50/50 flex flex-col justify-between space-y-3"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded bg-gray-200 text-gray-700">
                    {claim.category}
                  </span>
                  <TrustStatusBadge status={claim.trust_status} size="sm" />
                </div>
                <p className="text-xs font-sans text-gray-900 mt-2 font-medium">
                  &ldquo;{claim.claim_text}&rdquo;
                </p>
              </div>

              <div className="pt-2 border-t border-gray-200/60 flex items-center justify-between text-[10px] font-mono text-gray-500">
                <span>Type: {claim.claim_type}</span>
                <span>Confidence: {Math.round(claim.confidence * 100)}%</span>
              </div>
            </div>
          ))}
        </div>

        {/* Applications & Keywords */}
        {product.target_applications.length > 0 && (
          <div className="pt-4 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-gray-700 font-sans">Target Applications:</span>
              {product.target_applications.map((app, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 bg-brand-dark/5 text-brand-dark rounded border border-brand-dark/10 font-mono text-[11px]"
                >
                  {app}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Human Resolution Modal */}
      <ReviewResolveModal
        item={selectedReviewItem}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onResolvedSuccess={handleResolvedSuccess}
      />
    </div>
  );
}
