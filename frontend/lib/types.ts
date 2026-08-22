/**
 * ProductIQ TypeScript Definitions — Phase 6 Frontend
 * Aligned precisely with FastAPI DTOs and Phase 0–5 domain models.
 */

export type TrustStatus =
  | "TRUSTED"
  | "REVIEW_REQUIRED"
  | "CONFLICTED"
  | "UNVERIFIED"
  | "UNSUPPORTED"
  | "MISSING";

export type PublishabilityStatus =
  | "PUBLISHABLE"
  | "PUBLISHABLE_WITH_WARNING"
  | "REVIEW_REQUIRED"
  | "NOT_PUBLISHABLE";

export type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface Specification {
  field: string;
  canonical_value: any;
  canonical_unit: string | null;
  trust_status: TrustStatus;
  publishability: PublishabilityStatus;
  validation_status?: string;
  is_conflicted: boolean;
  evidence_sources: string[];
  confidence_score: number;
  reason: string;
  validation_rule_ids: string[];
}

export interface Claim {
  claim_text: string;
  category: string;
  claim_type: "SOURCE_BACKED" | "INFERRED" | "UNSUPPORTED";
  trust_status: TrustStatus;
  publishability: PublishabilityStatus;
  supporting_fields: string[];
  evidence_sources: string[];
  confidence: number;
  reason: string;
}

export interface ConflictSource {
  source_id?: string;
  source_type?: string;          // "pdf" | "csv" | "web" | "manual"
  source_name?: string;          // "PDF Brochure (Official)"
  value?: any;
  unit?: string | null;
  raw_value?: string | null;
  location?: string | null;      // "p.5, 4-pole electrical data table"
  confidence?: number | null;
}

export interface ConflictRecord {
  field: string;
  canonical_field?: string;
  description?: string;
  action_needed?: string;
  recommended_action?: string;
  sources: ConflictSource[];
  conflicting_values?: any[];
}

export interface ReviewItem {
  review_id: string;
  product_id: string;
  target_type: "attribute" | "claim" | "validation";
  target_name: string;
  severity: SeverityLevel;
  issue_type: "CONFLICT" | "WARNING" | "FAIL" | "UNVERIFIED_INFERENCE" | "MISSING_DATA";
  description: string;
  conflicting_values?: Array<{
    source_a?: string;
    value_a?: any;
    unit_a?: string;
    raw_a?: string;
    source_b?: string;
    value_b?: any;
    unit_b?: string;
    raw_b?: string;
  }>;
  conflicting_sources?: ConflictSource[];
  validation_rule_id?: string;
  affected_claims: string[];
  recommended_action: string;
  status: "OPEN" | "RESOLVED" | "DISMISSED";
  resolution_note?: string | null;
  resolved_value?: any;
  resolved_by?: string | null;
}

export interface EvidenceRecord {
  source_id: string;
  source_type: "pdf" | "csv" | "web" | "llm-enrichment";
  product_id: string;
  attribute: string;
  raw_value: string;
  raw_unit?: string | null;
  parsed_value?: any;
  method: string;
  confidence: number;
  page?: number | null;
  row?: number | null;
  column?: string | null;
  url?: string | null;
  section?: string | null;
  evidence_text?: string | null;
}

export interface ProductSummary {
  product_id: string;
  manufacturer: string;
  model: string;
  category: string;
  trust_score: number;
  overall_trust_status: TrustStatus;
  overall_publishability: PublishabilityStatus;
  review_items_count: number;
  conflicts_count: number;
  publishable_attributes_count: number;
  restricted_attributes_count: number;
  rated_power_kw?: number | null;
  rated_voltage_v?: number | null;
  rated_speed_rpm?: number | null;
  poles?: number | null;
  frame_size?: string | null;
  summary_reason: string;
}

export interface ProductDetail {
  product_id: string;
  manufacturer: string;
  model: string;
  category: string;
  trust_score: number;
  trust_score_formula: string;
  trust_score_breakdown: {
    completeness_score?: number;
    validity_score?: number;
    diversity_score?: number;
    conflict_penalty?: number;
    completeness_weight?: number;
    validity_weight?: number;
    diversity_weight?: number;
  };
  overall_trust_status: TrustStatus;
  overall_publishability: PublishabilityStatus;
  summary_reason: string;
  specifications: Record<string, Specification>;
  claims: Claim[];
  review_queue: ReviewItem[];
  unresolved_conflicts: ConflictRecord[];
  publishable_attributes: string[];
  restricted_attributes: string[];
  evidence_records: EvidenceRecord[];
  commercial_summary: string;
  technical_description: string;
  target_applications: string[];
  search_keywords: string[];
}

export interface BatchSummary {
  total_products: number;
  trusted_count: number;
  review_required_count: number;
  conflicted_count: number;
  publishable_count: number;
  publishable_with_warning_count: number;
  not_publishable_count: number;
  avg_trust_score: number;
  total_review_items: number;
  trust_distribution: Record<string, number>;
  publishability_distribution: Record<string, number>;
  severity_distribution: Record<string, number>;
  products: ProductSummary[];
  generated_at: string;
}

export interface ReviewResolutionRequest {
  selected_source?: string;
  resolved_value: any;
  resolution_note: string;
  reviewer?: string;
}

export interface ReviewResolutionResponse {
  success: boolean;
  review_id: string;
  product_id: string;
  status: string;
  resolved_value: any;
  message: string;
}

// -------------------------------------------------------------
// Catalog Intelligence (Unilog Pivot) Types
// -------------------------------------------------------------

export type CatalogTrustStatusType = "Verified" | "Inferred" | "Conflicted" | "Unknown";

export interface CatalogFieldDTO<T = any> {
  value: T | null;
  status: CatalogTrustStatusType;
  confidence: number;
  sources: string[];
  reason: string;
}

export interface CatalogAttributeTripleDTO {
  label: string;
  value: any;
  uom: string | null;
  raw_value: string | null;
  raw_uom: string | null;
  status: CatalogTrustStatusType;
  confidence: number;
  reason: string;
}

export interface CatalogProductDTO {
  row_id: number;
  mfg_part_num: string;
  part_desc: string | null;
  raw_input: {
    row_id: number;
    mfg_part_num: string;
    part_desc: string | null;
    e1_brand: string | null;
    unilog_brand: string | null;
    dib_brand: string | null;
    part_manuf: string | null;
  };
  manufacturer_name: CatalogFieldDTO<string>;
  brand_name: CatalogFieldDTO<string>;
  trade_name: CatalogFieldDTO<string>;
  manufacturer_part_number: CatalogFieldDTO<string>;
  product_name: CatalogFieldDTO<string>;
  series: CatalogFieldDTO<string>;
  classpath: CatalogFieldDTO<string>;
  attributes: CatalogAttributeTripleDTO[];
  short_desc: CatalogFieldDTO<string>;
  long_desc: CatalogFieldDTO<string>;
  overall_trust_status: CatalogTrustStatusType;
  overall_confidence: number;
  has_conflicts: boolean;
  unresolved_conflicts: Array<{
    field: string;
    sources: string[];
    reason: string;
  }>;
}

export interface CatalogProductSummaryDTO {
  row_id: number;
  mfg_part_num: string;
  part_desc: string | null;
  manufacturer: string | null;
  brand: string | null;
  overall_status: CatalogTrustStatusType;
  confidence: number;
  has_conflicts: boolean;
}

export interface CatalogProductsListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: CatalogProductSummaryDTO[];
}

export interface CatalogExactMatchFieldComparison {
  field_name: string;
  pipeline_value: string | null;
  expected_value: string | null;
  is_exact_match: boolean;
  status_tier: string;
  confidence: number;
}

export interface CatalogExactMatchRow {
  row_id: number;
  mfg_part_num: string;
  fields_compared: number;
  fields_matched: number;
  row_accuracy_pct: number;
  field_comparisons: CatalogExactMatchFieldComparison[];
}

export interface CatalogExactMatchEvalDTO {
  evaluation_name: string;
  metric_label: string;
  sample_size_n: number;
  sample_size_label: string;
  total_fields_compared: number;
  total_fields_matched: number;
  overall_exact_match_rate_pct: number;
  summary_statement: string;
  disclaimer: string;
  rows: CatalogExactMatchRow[];
}

export interface CatalogStatusDistributionBreakdown {
  verified_count: number;
  inferred_count: number;
  conflicted_count: number;
  unknown_count: number;
  verified_pct: number;
  inferred_pct: number;
  conflicted_pct: number;
  unknown_pct: number;
}

export interface CatalogComplianceEvalDTO {
  evaluation_name: string;
  total_input_rows: number;
  description: string;
  lov_compliance_rate_pct: number;
  lov_compliance_note: string;
  total_conflicts_detected: number;
  conflict_detection_rate_pct: number;
  conflict_examples: Array<{
    row_id: number;
    mfg_part_num: string;
    part_desc: string | null;
    reason: string;
    sources: string[];
  }>;
  total_placeholders_filtered: number;
  rows_with_placeholders_filtered: number;
  placeholder_filtering_rate_pct: number;
  manufacturer_status_distribution: CatalogStatusDistributionBreakdown;
  brand_status_distribution: CatalogStatusDistributionBreakdown;
  overall_status_distribution: CatalogStatusDistributionBreakdown;
  total_duration_ms: number;
  throughput_rows_per_second: number;
  avg_latency_ms_per_row: number;
}

