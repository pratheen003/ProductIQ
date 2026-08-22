"""
ProductIQ API Test Suite — Phase 6
===================================
Tests for all REST endpoints in the FastAPI service bridge.
"""
import pytest
from fastapi.testclient import TestClient

from productiq.api.app import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "6.0.0"


def test_list_products():
    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    assert len(products) == 12

    # Verify key fields
    p0 = products[0]
    assert "product_id" in p0
    assert "trust_score" in p0
    assert "overall_trust_status" in p0
    assert "overall_publishability" in p0


def test_get_product_detail():
    demo_id = "PIQ-W22SP-4P-1.1"
    response = client.get(f"/api/products/{demo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == demo_id
    assert "specifications" in data
    assert "rated_voltage" in data["specifications"]
    assert "rated_current" in data["specifications"]

    # Verify rated_voltage is trusted and 400.0 V
    v_spec = data["specifications"]["rated_voltage"]
    assert v_spec["canonical_value"] == 400.0
    assert v_spec["trust_status"] == "TRUSTED"
    assert v_spec["publishability"] == "PUBLISHABLE"

    # Verify rated_current is conflicted and null
    c_spec = data["specifications"]["rated_current"]
    assert c_spec["canonical_value"] is None
    assert c_spec["trust_status"] == "CONFLICTED"
    assert c_spec["publishability"] == "REVIEW_REQUIRED"


def test_get_product_trust():
    demo_id = "PIQ-W22SP-4P-1.1"
    response = client.get(f"/api/products/{demo_id}/trust")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == demo_id
    assert "trust_score_formula" in data
    assert "review_queue" in data


def test_get_product_evidence():
    demo_id = "PIQ-W22SP-4P-1.1"
    response = client.get(f"/api/products/{demo_id}/evidence")
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert len(data["records"]) > 0


def test_get_batch_summary():
    response = client.get("/api/batch/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_products"] == 12
    assert data["total_review_items"] == 62
    assert data["avg_trust_score"] > 0.0
    assert "trust_distribution" in data
    assert "severity_distribution" in data


def test_list_reviews():
    response = client.get("/api/reviews")
    assert response.status_code == 200
    reviews = response.json()
    assert isinstance(reviews, list)
    assert len(reviews) == 62

    # Filter by severity
    high_resp = client.get("/api/reviews?severity=HIGH")
    assert high_resp.status_code == 200
    high_reviews = high_resp.json()
    assert all(r["severity"] == "HIGH" for r in high_reviews)


def test_resolve_review_workflow():
    # Fetch a review ID from list
    reviews_resp = client.get("/api/reviews")
    reviews = reviews_resp.json()
    assert len(reviews) > 0
    target_id = reviews[0]["review_id"]

    # Post resolution
    res_payload = {
        "selected_source": "pdf",
        "resolved_value": "2.34 A",
        "resolution_note": "Verified from manufacturer physical catalog datasheet page 5.",
        "reviewer": "Senior Application Engineer",
    }
    resolve_resp = client.post(f"/api/reviews/{target_id}/resolve", json=res_payload)
    assert resolve_resp.status_code == 200
    res_data = resolve_resp.json()
    assert res_data["success"] is True
    assert res_data["status"] == "RESOLVED"

    # Verify review detail reflects resolution
    get_resp = client.get(f"/api/reviews/{target_id}")
    assert get_resp.status_code == 200
    updated_review = get_resp.json()
    assert updated_review["status"] == "RESOLVED"
    assert updated_review["resolution_note"] == res_payload["resolution_note"]


def test_ingest_demo_status():
    response = client.post("/api/ingest/demo-run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETE"
    assert len(data["stages"]) == 5
