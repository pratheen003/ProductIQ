import {
  ProductSummary,
  ProductDetail,
  BatchSummary,
  ReviewItem,
  ReviewResolutionRequest,
  ReviewResolutionResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
      next: { revalidate: 0 }, // always fresh in dev
    });

    if (!res.ok) {
      const errorBody = await res.text();
      throw new Error(`API Error ${res.status}: ${errorBody || res.statusText}`);
    }

    return (await res.json()) as T;
  } catch (error: any) {
    console.error(`Fetch error on ${url}:`, error);
    throw error;
  }
}

export const api = {
  // Health
  checkHealth: () => fetchAPI<{ status: string; service: string; version: string }>("/health"),

  // Products
  getProducts: (params?: { search?: string; status?: string; publishability?: string }) => {
    const q = new URLSearchParams();
    if (params?.search) q.append("search", params.search);
    if (params?.status) q.append("status", params.status);
    if (params?.publishability) q.append("publishability", params.publishability);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return fetchAPI<ProductSummary[]>(`/products${qs}`);
  },

  getProductDetail: (productId: string) =>
    fetchAPI<ProductDetail>(`/products/${encodeURIComponent(productId)}`),

  getProductTrust: (productId: string) =>
    fetchAPI<any>(`/products/${encodeURIComponent(productId)}/trust`),

  getProductEvidence: (productId: string) =>
    fetchAPI<{ product_id: string; total_records: number; records: any[] }>(
      `/products/${encodeURIComponent(productId)}/evidence`
    ),

  getProductEnrichment: (productId: string) =>
    fetchAPI<any>(`/products/${encodeURIComponent(productId)}/enrichment`),

  // Batch
  getBatchSummary: () => fetchAPI<BatchSummary>("/batch/summary"),

  // Reviews
  getReviews: (params?: {
    severity?: string;
    issue_type?: string;
    status?: string;
    product_id?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.severity) q.append("severity", params.severity);
    if (params?.issue_type) q.append("issue_type", params.issue_type);
    if (params?.status) q.append("status", params.status);
    if (params?.product_id) q.append("product_id", params.product_id);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return fetchAPI<ReviewItem[]>(`/reviews${qs}`);
  },

  getReview: (reviewId: string) =>
    fetchAPI<ReviewItem>(`/reviews/${encodeURIComponent(reviewId)}`),

  resolveReview: (reviewId: string, payload: ReviewResolutionRequest) =>
    fetchAPI<ReviewResolutionResponse>(`/reviews/${encodeURIComponent(reviewId)}/resolve`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Ingestion
  triggerDemoIngest: () =>
    fetchAPI<{
      pipeline_id: string;
      current_stage: string;
      status: string;
      stages: any[];
      total_records_extracted: number;
      products_discovered: number;
    }>("/ingest/demo-run", { method: "POST" }),

  // -----------------------------------------------------------
  // Catalog Intelligence (Unilog Pivot) API Methods
  // -----------------------------------------------------------
  getCatalogProducts: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    search?: string;
    has_conflicts?: boolean;
  }) => {
    const q = new URLSearchParams();
    if (params?.page) q.append("page", params.page.toString());
    if (params?.page_size) q.append("page_size", params.page_size.toString());
    if (params?.status) q.append("status", params.status);
    if (params?.search) q.append("search", params.search);
    if (params?.has_conflicts !== undefined) q.append("has_conflicts", params.has_conflicts.toString());
    const qs = q.toString() ? `?${q.toString()}` : "";
    return fetchAPI<import("./types").CatalogProductsListResponse>(`/catalog/products${qs}`);
  },

  getCatalogProductDetail: (rowId: number) =>
    fetchAPI<import("./types").CatalogProductDTO>(`/catalog/products/${rowId}`),

  getCatalogBatchSummary: () =>
    fetchAPI<any>("/catalog/batch/summary"),

  getCatalogExactMatchEval: () =>
    fetchAPI<import("./types").CatalogExactMatchEvalDTO>("/catalog/eval/exact-match"),

  getCatalogComplianceEval: () =>
    fetchAPI<import("./types").CatalogComplianceEvalDTO>("/catalog/eval/compliance"),

  enrichCatalogRow: (rowId: number) =>
    fetchAPI<import("./types").CatalogProductDTO>(`/catalog/enrich/${rowId}`, {
      method: "POST",
    }),
};
