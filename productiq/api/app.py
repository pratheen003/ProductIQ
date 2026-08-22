"""
ProductIQ FastAPI Application — Phase 6
========================================
Main REST API service for ProductIQ frontend and third-party integrations.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from productiq.api.models import (
    ProductSummaryDTO,
    ProductDetailDTO,
    BatchSummaryDTO,
    ReviewItemDTO,
    ReviewResolutionRequestDTO,
    ReviewResolutionResponseDTO,
    IngestStatusDTO,
)
from productiq.api.service import ProductIQDataBridge

logger = logging.getLogger("productiq.api")

app = FastAPI(
    title="ProductIQ API",
    description="REST API for ProductIQ Trust-Aware Industrial Product Intelligence",
    version="6.0.0",
)

# Enable CORS for Next.js frontend (localhost:3000, 3001, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bridge = ProductIQDataBridge()


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ProductIQ API", "version": "6.0.0"}


@app.get("/api/products", response_model=List[ProductSummaryDTO], tags=["Products"])
def list_products(
    search: Optional[str] = Query(None, description="Search term across product ID, model, or manufacturer"),
    status: Optional[str] = Query(None, description="Filter by trust status (TRUSTED, CONFLICTED, etc.)"),
    publishability: Optional[str] = Query(None, description="Filter by publishability status"),
):
    """
    List all processed industrial motor products with trust metrics.
    """
    products = bridge.get_all_products()

    if search:
        s = search.lower()
        products = [
            p for p in products
            if s in p.product_id.lower() or s in p.model.lower() or s in p.manufacturer.lower() or s in p.category.lower()
        ]

    if status:
        products = [p for p in products if p.overall_trust_status.upper() == status.upper()]

    if publishability:
        products = [p for p in products if p.overall_publishability.upper() == publishability.upper()]

    return products


@app.get("/api/products/{product_id}", response_model=ProductDetailDTO, tags=["Products"])
def get_product(product_id: str):
    """
    Retrieve full unified technical specifications, trust report, evidence records, and claims for a product.
    """
    product = bridge.get_product_detail(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found.",
        )
    return product


@app.get("/api/products/{product_id}/trust", tags=["Trust"])
def get_product_trust(product_id: str):
    """
    Get trust evaluation, formula breakdown, and review queue for a single product.
    """
    product = bridge.get_product_detail(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found.",
        )
    return {
        "product_id": product.product_id,
        "trust_score": product.trust_score,
        "trust_score_formula": product.trust_score_formula,
        "trust_score_breakdown": product.trust_score_breakdown,
        "overall_trust_status": product.overall_trust_status,
        "overall_publishability": product.overall_publishability,
        "summary_reason": product.summary_reason,
        "attribute_trust": product.specifications,
        "review_queue": product.review_queue,
        "unresolved_conflicts": product.unresolved_conflicts,
        "publishable_attributes": product.publishable_attributes,
        "restricted_attributes": product.restricted_attributes,
    }


@app.get("/api/products/{product_id}/evidence", tags=["Evidence"])
def get_product_evidence(product_id: str):
    """
    Get all raw evidence records extracted from PDF, CSV, and Web for a product.
    """
    product = bridge.get_product_detail(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found.",
        )
    return {
        "product_id": product.product_id,
        "total_records": len(product.evidence_records),
        "records": product.evidence_records,
    }


@app.get("/api/products/{product_id}/enrichment", tags=["Enrichment"])
def get_product_enrichment(product_id: str):
    """
    Get grounded AI enrichment synthesis, claims, applications, and search keywords for a product.
    """
    product = bridge.get_product_detail(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found.",
        )
    return {
        "product_id": product.product_id,
        "commercial_summary": product.commercial_summary,
        "technical_description": product.technical_description,
        "target_applications": product.target_applications,
        "search_keywords": product.search_keywords,
        "claims": product.claims,
    }


@app.get("/api/batch/summary", response_model=BatchSummaryDTO, tags=["Batch"])
def get_batch_summary():
    """
    Retrieve dataset-wide intelligence metrics, trust distributions, and publishability readiness.
    """
    return bridge.get_batch_summary()


@app.get("/api/reviews", response_model=List[ReviewItemDTO], tags=["Review Queue"])
def list_reviews(
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    issue_type: Optional[str] = Query(None, description="Filter by issue type (CONFLICT, WARNING, FAIL)"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN, RESOLVED)"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
):
    """
    Retrieve review queue items across all products with filtering.
    """
    reviews = bridge.get_all_reviews(severity=severity, issue_type=issue_type, status=status)
    if product_id:
        reviews = [r for r in reviews if r.product_id == product_id]
    return reviews


@app.get("/api/reviews/{review_id}", response_model=ReviewItemDTO, tags=["Review Queue"])
def get_review_item(review_id: str):
    """
    Retrieve a specific review item by review ID.
    """
    review = bridge.get_review(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item '{review_id}' not found.",
        )
    return review


@app.post("/api/reviews/{review_id}/resolve", response_model=ReviewResolutionResponseDTO, tags=["Review Queue"])
def resolve_review_item(review_id: str, request: ReviewResolutionRequestDTO):
    """
    Submit a human domain engineer resolution for a conflicted specification or review item.
    """
    result = bridge.resolve_review(review_id, request)
    if not result.success and result.status == "NOT_FOUND":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.message,
        )
    return result


@app.post("/api/ingest/demo-run", response_model=IngestStatusDTO, tags=["Ingestion"])
def trigger_demo_ingest():
    """
    Simulate or trigger pipeline execution for demonstration.
    """
    return IngestStatusDTO(
        pipeline_id="PIPE-RUN-20260820-001",
        current_stage="COMPLETE",
        status="COMPLETE",
        stages=[
            {"id": "extract", "name": "Multi-Source Extraction", "status": "COMPLETE", "records": 1837, "duration_s": 1.2},
            {"id": "normalize", "name": "Canonical Normalization", "status": "COMPLETE", "records": 12, "duration_s": 0.4},
            {"id": "validate", "name": "Physics & Engineering Validation", "status": "COMPLETE", "findings": 409, "duration_s": 0.8},
            {"id": "enrich", "name": "Grounded AI Enrichment", "status": "COMPLETE", "claims": 87, "duration_s": 2.5},
            {"id": "trust", "name": "Trust Intelligence Evaluation", "status": "COMPLETE", "reviews": 62, "duration_s": 0.3},
        ],
        total_records_extracted=1837,
        products_discovered=12,
    )


# Mount Unilog Catalog Pipeline Routes (Parallel Workstream)
try:
    from productiq_catalog.api import catalog_router
    app.include_router(catalog_router)
except ImportError as e:
    logger.warning(f"Could not import catalog_router: {e}")

