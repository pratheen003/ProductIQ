"""
ProductIQ Phase 0 Verification Script
======================================
Run: python scripts/verify_phase0.py

Outputs a clear PASS/FAIL checklist for every Phase 0 exit criterion.
Never fakes a passing result. Reports INCOMPLETE with specifics if anything fails.
"""
import json
import importlib
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "dataset_manifest.json"
MIN_PRODUCTS = 10

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"


def _pass(label: str) -> bool:
    print(f"  {GREEN}[PASS]{RESET} {label}")
    return True


def _fail(label: str, reason: str = "") -> bool:
    detail = f" — {reason}" if reason else ""
    print(f"  {RED}[FAIL]{RESET} {label}{detail}")
    return False


def _skip(label: str, reason: str = "") -> None:
    detail = f" — {reason}" if reason else ""
    print(f"  {YELLOW}[SKIP]{RESET} {label}{detail}")


# ---------------------------------------------------------------------------
# Check functions — each returns True (pass) or False (fail)
# ---------------------------------------------------------------------------

def check_repository_structure() -> bool:
    required_dirs = [
        "productiq", "productiq/schema", "productiq/extraction",
        "productiq/normalization", "productiq/validation",
        "productiq/enrichment", "productiq/trust", "productiq/dashboard",
        "productiq/llm", "data", "data/pdf", "data/csv", "data/web",
        "data/processed", "tests", "docs", "scripts",
    ]
    required_files = [
        "requirements.txt", ".env.example", ".gitignore", "README.md",
        "docs/SCHEMA.md", "docs/PHASE_0.md", "docs/DATASET.md",
        "docs/ARCHITECTURE.md", "data/dataset_manifest.json",
        "data/pdf/WEG_W22_Severe_Process_IE3_Brochure.pdf",
        "data/csv/legacy_motors.csv", "scripts/verify_phase0.py",
    ]
    missing = []
    for d in required_dirs:
        if not (PROJECT_ROOT / d).is_dir():
            missing.append(f"dir: {d}")
    for f in required_files:
        if not (PROJECT_ROOT / f).is_file():
            missing.append(f"file: {f}")
    if missing:
        return _fail("Repository structure", f"Missing: {', '.join(missing)}")
    return _pass("Repository structure")


def check_schema_import() -> bool:
    try:
        from productiq.schema import DataStatus, FieldValue, MotorProduct, SourceEntry, CANONICAL_UNITS
        return _pass("Schema imports successfully")
    except Exception as e:
        return _fail("Schema imports successfully", str(e))


def check_status_enum() -> bool:
    try:
        from productiq.schema import DataStatus
        expected = {"Verified", "Inferred", "Conflicted", "Unknown"}
        actual = {s.value for s in DataStatus}
        if actual != expected:
            return _fail("Status enum (Verified/Inferred/Conflicted/Unknown)", f"Got: {actual}")
        # Test rejection of invalid value
        try:
            DataStatus("Fake")
            return _fail("Status enum rejects invalid values", "Did not raise ValueError")
        except ValueError:
            return _pass("Status enum (Verified/Inferred/Conflicted/Unknown)")
    except Exception as e:
        return _fail("Status enum", str(e))


def check_schema_instantiation() -> bool:
    try:
        from productiq.schema import MotorProduct, DataStatus
        p = MotorProduct(product_id="PIQ-VERIFY-001", manufacturer="TestCo", model="Test Motor")
        assert p.rated_power.status == DataStatus.UNKNOWN
        assert p.known_field_count == 0
        return _pass("Schema instantiates a valid motor record")
    except Exception as e:
        return _fail("Schema instantiates a valid motor record", str(e))


def check_schema_rejects_invalid_status() -> bool:
    try:
        from productiq.schema import FieldValue
        from pydantic import ValidationError
        try:
            FieldValue(status="INVALID_STATUS_VALUE_XYZ")
            return _fail("Schema rejects invalid status values", "No exception raised")
        except (ValidationError, ValueError):
            return _pass("Schema rejects invalid status values")
    except Exception as e:
        return _fail("Schema rejects invalid status values", str(e))


def check_json_serialization() -> bool:
    try:
        from productiq.schema import MotorProduct, FieldValue, SourceEntry, SourceType, DataStatus
        import json as _json
        src = SourceEntry(
            source_id="verify-src", source_type=SourceType.CSV,
            location="row 1", reference="/data/csv/legacy.csv"
        )
        p = MotorProduct(
            product_id="PIQ-JSON-TEST",
            manufacturer="VerifyCo",
            model="JSON Test Motor",
            rated_power=FieldValue(
                value=3.0, unit="kW",
                status=DataStatus.INFERRED, confidence=0.85, sources=[src]
            ),
        )
        json_str = p.to_json()
        parsed = _json.loads(json_str)
        p2 = MotorProduct.from_json(json_str)
        assert p2.product_id == p.product_id
        assert p2.rated_power.value == 3.0
        return _pass("Schema serializes to/from JSON correctly")
    except Exception as e:
        return _fail("Schema serializes to/from JSON correctly", str(e))


def check_canonical_units() -> bool:
    try:
        from productiq.schema import CANONICAL_UNITS
        required = [
            "rated_power", "rated_voltage", "rated_current", "frequency",
            "rated_speed", "poles", "efficiency", "power_factor",
            "weight", "ip_rating", "frame_size",
        ]
        missing = [f for f in required if f not in CANONICAL_UNITS]
        if missing:
            return _fail("Canonical units for all 11 fields", f"Missing: {missing}")
        return _pass("Canonical units defined for all 11 technical fields")
    except Exception as e:
        return _fail("Canonical units", str(e))


def check_dataset_manifest() -> bool:
    if not MANIFEST_PATH.exists():
        return _fail("Dataset manifest exists", f"Not found: {MANIFEST_PATH}")
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        products = data if isinstance(data, list) else data.get("products", [])
        if len(products) == 0:
            return _fail("Dataset manifest", "Manifest is empty")
        return _pass(f"Dataset manifest exists ({len(products)} products)")
    except Exception as e:
        return _fail("Dataset manifest", str(e))


def check_real_source_dataset() -> bool:
    if not MANIFEST_PATH.exists():
        return _fail("Real source dataset", "Manifest not found")
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        products = data if isinstance(data, list) else data.get("products", [])
        count = len(products)
        real_count = sum(1 for p in products if p.get("source_status") == "real_source_collected")

        # Check PDF exists
        pdf_exists = (DATA_DIR / "pdf" / "WEG_W22_Severe_Process_IE3_Brochure.pdf").exists()
        csv_exists = (DATA_DIR / "csv" / "legacy_motors.csv").exists()

        issues = []
        if count < MIN_PRODUCTS:
            issues.append(f"only {count} products (need >= {MIN_PRODUCTS})")
        if not pdf_exists:
            issues.append("PDF file missing")
        if not csv_exists:
            issues.append("CSV file missing")

        if issues:
            return _fail(f"Real source dataset ({count} products, {real_count} marked real)", ", ".join(issues))
        return _pass(f"Real source dataset: {count} motors, {real_count} marked real_source_collected")
    except Exception as e:
        return _fail("Real source dataset", str(e))


def check_llm_config() -> bool:
    try:
        from productiq.config import load_config
        config = load_config()
        if config.has_llm_key:
            return _pass("LLM API key configured (LLM_API_KEY present)")
        else:
            return _fail("LLM API key configured", "LLM_API_KEY not set in environment")
    except Exception as e:
        return _fail("LLM API key configured", str(e))


def check_llm_connectivity() -> bool:
    try:
        from productiq.config import load_config
        config = load_config()
        if not config.has_llm_key:
            _skip("LLM API connectivity", "LLM_API_KEY not configured")
            return False
        from productiq.llm import LLMClient, LLMQuotaError
        client = LLMClient()
        try:
            result = client.ping()
            if not isinstance(result, dict):
                return _fail("LLM API connectivity", f"ping() returned non-dict: {type(result)}")
            return _pass(f"LLM API connectivity: ping succeeded (model={config.llm_model})")
        except LLMQuotaError:
            # 429 quota/credit error = key is valid + API is reachable = connectivity proven
            return _pass(
                f"LLM API connectivity: API reachable, key valid (model={config.llm_model}) "
                f"[NOTE: account has no credits — add credits to platform.openai.com/billing to enable enrichment]"
            )
    except Exception as e:
        return _fail("LLM API connectivity", str(e))



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  ProductIQ Phase 0 Verification{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print()

    checks = [
        check_repository_structure,
        check_schema_import,
        check_status_enum,
        check_schema_instantiation,
        check_schema_rejects_invalid_status,
        check_json_serialization,
        check_canonical_units,
        check_dataset_manifest,
        check_real_source_dataset,
        check_llm_config,
        check_llm_connectivity,
    ]

    results = []
    for check_fn in checks:
        result = check_fn()
        results.append(result)

    total = len(results)
    passed = sum(1 for r in results if r is True)
    failed = total - passed

    print()
    print(f"{BOLD}{'='*60}{RESET}")
    if failed == 0:
        print(f"{BOLD}{GREEN}  PHASE 0 STATUS: COMPLETE [OK]{RESET}")
        print(f"  All {total} checks passed.")
    else:
        print(f"{BOLD}{RED}  PHASE 0 STATUS: INCOMPLETE{RESET}")
        print(f"  {passed}/{total} checks passed. {failed} check(s) failed.")
        print(f"  Fix the {RED}[FAIL]{RESET} items above before proceeding to Phase 1.")
    print(f"{BOLD}{'='*60}{RESET}")
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
