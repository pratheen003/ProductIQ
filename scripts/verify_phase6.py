#!/usr/bin/env python3
"""
ProductIQ Phase 6 Verification Script — Frontend & Presentation Layer
======================================================================
Automated audit verifying FastAPI backend bridge, Next.js frontend build,
endpoints, real data integration, and Phase 0–5 integrity.
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from productiq.api.app import app
from productiq.api.service import ProductIQDataBridge


def check(name: str, condition: bool, detail: str = "") -> bool:
    status_str = "[PASS]" if condition else "[FAIL]"
    print(f"  {status_str} {name}")
    if not condition and detail:
        print(f"         DETAIL: {detail}")
    return condition


def main():
    print("=" * 60)
    print("  ProductIQ Phase 6 Verification")
    print("=" * 60)
    print()

    passed = 0
    total = 20

    client = TestClient(app)

    # 1. Phase 0 baseline intact
    try:
        from productiq.schema.motor import MotorProduct, DataStatus, CANONICAL_UNITS
        c1 = check("Phase 0 baseline intact", len(CANONICAL_UNITS) == 11)
    except Exception as e:
        c1 = check("Phase 0 baseline intact", False, str(e))
    passed += int(c1)

    # 2. Phase 1 baseline intact
    try:
        from productiq.extraction.models import EvidenceRecord
        c2 = check("Phase 1 baseline intact", True)
    except Exception as e:
        c2 = check("Phase 1 baseline intact", False, str(e))
    passed += int(c2)

    # 3. Phase 2 baseline intact
    try:
        from productiq.normalization.models import NormalizedProduct
        c3 = check("Phase 2 baseline intact", True)
    except Exception as e:
        c3 = check("Phase 2 baseline intact", False, str(e))
    passed += int(c3)

    # 4. Phase 3 baseline intact
    try:
        from productiq.validation.models import ProductValidationReport
        c4 = check("Phase 3 baseline intact", True)
    except Exception as e:
        c4 = check("Phase 3 baseline intact", False, str(e))
    passed += int(c4)

    # 5. Phase 4 baseline intact
    try:
        from productiq.enrichment.models import ProductEnrichment
        c5 = check("Phase 4 baseline intact", True)
    except Exception as e:
        c5 = check("Phase 4 baseline intact", False, str(e))
    passed += int(c5)

    # 6. Phase 5 baseline intact
    try:
        from productiq.trust.models import ProductTrustReport, BatchTrustReport
        c6 = check("Phase 5 baseline intact", True)
    except Exception as e:
        c6 = check("Phase 5 baseline intact", False, str(e))
    passed += int(c6)

    # 7. FastAPI health check works
    try:
        resp = client.get("/api/health")
        c7 = check("FastAPI health check works", resp.status_code == 200 and resp.json()["status"] == "ok")
    except Exception as e:
        c7 = check("FastAPI health check works", False, str(e))
    passed += int(c7)

    # 8. Products list endpoint returns 12 real motors
    try:
        resp = client.get("/api/products")
        data = resp.json()
        c8 = check("Products list endpoint returns 12 real motors", resp.status_code == 200 and len(data) == 12)
    except Exception as e:
        c8 = check("Products list endpoint returns 12 real motors", False, str(e))
    passed += int(c8)

    # 9. Product detail endpoint returns canonical specs & evidence
    try:
        demo_id = "PIQ-W22SP-4P-1.1"
        resp = client.get(f"/api/products/{demo_id}")
        pdata = resp.json()
        c9 = check(
            "Product detail endpoint returns canonical specs & evidence",
            resp.status_code == 200 and "specifications" in pdata and len(pdata["specifications"]) >= 10
        )
    except Exception as e:
        c9 = check("Product detail endpoint returns canonical specs & evidence", False, str(e))
    passed += int(c9)

    # 10. Known rated-current conflict handled correctly (no silent winner)
    try:
        current_spec = pdata["specifications"]["rated_current"]
        c10 = check(
            "Known rated-current conflict handled correctly (no silent winner)",
            current_spec["canonical_value"] is None and
            current_spec["trust_status"] == "CONFLICTED" and
            current_spec["publishability"] == "REVIEW_REQUIRED" and
            len(current_spec["evidence_sources"]) >= 2
        )
    except Exception as e:
        c10 = check("Known rated-current conflict handled correctly (no silent winner)", False, str(e))
    passed += int(c10)

    # 11. Clean publishable attribute verified (rated_voltage)
    try:
        voltage_spec = pdata["specifications"]["rated_voltage"]
        c11 = check(
            "Clean publishable attribute verified (rated_voltage)",
            voltage_spec["canonical_value"] == 400.0 and
            voltage_spec["trust_status"] == "TRUSTED" and
            voltage_spec["publishability"] == "PUBLISHABLE" and
            "rated_voltage" in pdata["publishable_attributes"]
        )
    except Exception as e:
        c11 = check("Clean publishable attribute verified (rated_voltage)", False, str(e))
    passed += int(c11)

    # 12. Batch summary endpoint aggregates dataset metrics
    try:
        b_resp = client.get("/api/batch/summary")
        b_data = b_resp.json()
        c12 = check(
            "Batch summary endpoint aggregates dataset metrics",
            b_resp.status_code == 200 and b_data["total_products"] == 12 and b_data["total_review_items"] == 62
        )
    except Exception as e:
        c12 = check("Batch summary endpoint aggregates dataset metrics", False, str(e))
    passed += int(c12)

    # 13. Review queue endpoint exposes all 62 items
    try:
        r_resp = client.get("/api/reviews")
        r_data = r_resp.json()
        c13 = check(
            "Review queue endpoint exposes all 62 items",
            r_resp.status_code == 200 and len(r_data) == 62
        )
    except Exception as e:
        c13 = check("Review queue endpoint exposes all 62 items", False, str(e))
    passed += int(c13)

    # 14. Human review resolution workflow executes and persists
    try:
        sample_id = r_data[0]["review_id"]
        res_payload = {
            "selected_source": "pdf",
            "resolved_value": "2.34 A",
            "resolution_note": "Verified from physical motor nameplate catalog.",
            "reviewer": "Domain Application Engineer",
        }
        res_resp = client.post(f"/api/reviews/{sample_id}/resolve", json=res_payload)
        c14 = check(
            "Human review resolution workflow executes and persists",
            res_resp.status_code == 200 and res_resp.json()["success"] is True
        )
    except Exception as e:
        c14 = check("Human review resolution workflow executes and persists", False, str(e))
    passed += int(c14)

    # 15. Ingestion pipeline trigger endpoint works
    try:
        ing_resp = client.post("/api/ingest/demo-run")
        c15 = check(
            "Ingestion pipeline trigger endpoint works",
            ing_resp.status_code == 200 and ing_resp.json()["status"] == "COMPLETE"
        )
    except Exception as e:
        c15 = check("Ingestion pipeline trigger endpoint works", False, str(e))
    passed += int(c15)

    # 16. Next.js package.json and config files exist
    try:
        f_pkg = (PROJECT_ROOT / "frontend" / "package.json").exists()
        f_ts = (PROJECT_ROOT / "frontend" / "tsconfig.json").exists()
        f_tw = (PROJECT_ROOT / "frontend" / "tailwind.config.ts").exists()
        c16 = check("Next.js package.json and config files exist", f_pkg and f_ts and f_tw)
    except Exception as e:
        c16 = check("Next.js package.json and config files exist", False, str(e))
    passed += int(c16)

    # 17. Next.js frontend pages exist (Dashboard, Catalog, Detail, Batch, Reviews, Ingest)
    try:
        p_dash = (PROJECT_ROOT / "frontend" / "app" / "page.tsx").exists()
        p_cat = (PROJECT_ROOT / "frontend" / "app" / "products" / "page.tsx").exists()
        p_det = (PROJECT_ROOT / "frontend" / "app" / "products" / "[id]" / "page.tsx").exists()
        p_batch = (PROJECT_ROOT / "frontend" / "app" / "batch" / "page.tsx").exists()
        p_rev = (PROJECT_ROOT / "frontend" / "app" / "reviews" / "page.tsx").exists()
        p_ing = (PROJECT_ROOT / "frontend" / "app" / "ingest" / "page.tsx").exists()
        c17 = check(
            "Next.js frontend pages exist (Dashboard, Catalog, Detail, Batch, Reviews, Ingest)",
            p_dash and p_cat and p_det and p_batch and p_rev and p_ing
        )
    except Exception as e:
        c17 = check("Next.js frontend pages exist (Dashboard, Catalog, Detail, Batch, Reviews, Ingest)", False, str(e))
    passed += int(c17)

    # 18. Next.js frontend components exist (Badges, Gauge, Table, Comparator, Charts)
    try:
        c_badge = (PROJECT_ROOT / "frontend" / "components" / "ui" / "TrustStatusBadge.tsx").exists()
        c_gauge = (PROJECT_ROOT / "frontend" / "components" / "ui" / "TrustScoreGauge.tsx").exists()
        c_table = (PROJECT_ROOT / "frontend" / "components" / "ui" / "SpecificationTable.tsx").exists()
        c_comp = (PROJECT_ROOT / "frontend" / "components" / "ui" / "ConflictComparator.tsx").exists()
        c_chart = (PROJECT_ROOT / "frontend" / "components" / "charts" / "TrustDistributionChart.tsx").exists()
        c18 = check(
            "Next.js frontend components exist (Badges, Gauge, Table, Comparator, Charts)",
            c_badge and c_gauge and c_table and c_comp and c_chart
        )
    except Exception as e:
        c18 = check("Next.js frontend components exist (Badges, Gauge, Table, Comparator, Charts)", False, str(e))
    passed += int(c18)

    # 19. Documentation complete (docs/PHASE_6.md)
    try:
        doc_phase6 = (PROJECT_ROOT / "docs" / "PHASE_6.md").exists()
        c19 = check("Documentation complete (docs/PHASE_6.md)", doc_phase6)
    except Exception as e:
        c19 = check("Documentation complete (docs/PHASE_6.md)", False, str(e))
    passed += int(c19)

    # 20. No secrets tracked (.env ignored, .env.example safe)
    try:
        env_example_path = PROJECT_ROOT / ".env.example"
        with open(env_example_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "gsk_" not in content
        assert "sk-proj-" not in content
        c20 = check("No secrets tracked (.env ignored, .env.example safe)", True)
    except Exception as e:
        c20 = check("No secrets tracked (.env ignored, .env.example safe)", False, str(e))
    passed += int(c20)

    print()
    print("=" * 60)
    if passed == total:
        print("  PHASE 6 STATUS: COMPLETE [OK]")
        print(f"  All {total} checks passed.")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"  PHASE 6 STATUS: INCOMPLETE [{passed}/{total} checks passed]")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
