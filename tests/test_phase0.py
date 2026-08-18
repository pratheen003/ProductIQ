"""
test_phase0.py
==============
Integration tests for Phase 0 exit criteria.

Tests:
- Repository directory structure exists
- All required Python modules can be imported
- Dataset manifest exists and has required structure
- Dataset contains >= 10 products
- All products have source_status field
- PDF file exists
- CSV file exists
- Web URL references exist for all products
- Source files referenced in manifest exist on disk
- Config loads without error
"""
import json
import os
import importlib
from pathlib import Path
import pytest

# Project root is parent of tests/
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "dataset_manifest.json"


# ---------------------------------------------------------------------------
# Repository structure
# ---------------------------------------------------------------------------

class TestRepositoryStructure:
    REQUIRED_DIRS = [
        "productiq",
        "productiq/schema",
        "productiq/extraction",
        "productiq/normalization",
        "productiq/validation",
        "productiq/enrichment",
        "productiq/trust",
        "productiq/dashboard",
        "productiq/llm",
        "data",
        "data/pdf",
        "data/csv",
        "data/web",
        "data/processed",
        "tests",
        "docs",
        "scripts",
    ]

    REQUIRED_FILES = [
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "README.md",
        "docs/SCHEMA.md",
        "docs/PHASE_0.md",
        "docs/DATASET.md",
        "docs/ARCHITECTURE.md",
        "data/dataset_manifest.json",
        "data/pdf/WEG_W22_Severe_Process_IE3_Brochure.pdf",
        "data/csv/legacy_motors.csv",
        "scripts/verify_phase0.py",
    ]

    @pytest.mark.parametrize("rel_path", REQUIRED_DIRS)
    def test_required_directory_exists(self, rel_path):
        target = PROJECT_ROOT / rel_path
        assert target.is_dir(), f"Required directory missing: {rel_path}"

    @pytest.mark.parametrize("rel_path", REQUIRED_FILES)
    def test_required_file_exists(self, rel_path):
        target = PROJECT_ROOT / rel_path
        assert target.is_file(), f"Required file missing: {rel_path}"


# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------

class TestModuleImports:
    REQUIRED_MODULES = [
        "productiq",
        "productiq.config",
        "productiq.logging_setup",
        "productiq.schema",
        "productiq.schema.motor",
        "productiq.extraction",
        "productiq.normalization",
        "productiq.validation",
        "productiq.enrichment",
        "productiq.trust",
        "productiq.dashboard",
        "productiq.llm",
        "productiq.llm.client",
    ]

    @pytest.mark.parametrize("module_name", REQUIRED_MODULES)
    def test_module_imports(self, module_name):
        try:
            mod = importlib.import_module(module_name)
            assert mod is not None
        except ImportError as e:
            pytest.fail(f"Failed to import '{module_name}': {e}")


# ---------------------------------------------------------------------------
# Schema symbols
# ---------------------------------------------------------------------------

class TestSchemaSymbols:
    def test_data_status_importable(self):
        from productiq.schema import DataStatus
        assert DataStatus is not None

    def test_motor_product_importable(self):
        from productiq.schema import MotorProduct
        assert MotorProduct is not None

    def test_field_value_importable(self):
        from productiq.schema import FieldValue
        assert FieldValue is not None

    def test_source_entry_importable(self):
        from productiq.schema import SourceEntry
        assert SourceEntry is not None

    def test_canonical_units_importable(self):
        from productiq.schema import CANONICAL_UNITS
        assert CANONICAL_UNITS is not None

    def test_status_enum_count(self):
        from productiq.schema import DataStatus
        assert len(DataStatus) == 4


# ---------------------------------------------------------------------------
# Dataset manifest
# ---------------------------------------------------------------------------

class TestDatasetManifest:
    @pytest.fixture(autouse=True)
    def load_manifest(self):
        assert MANIFEST_PATH.exists(), "dataset_manifest.json not found"
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Support both bare list and wrapped object
        if isinstance(data, list):
            self.products = data
        elif isinstance(data, dict) and "products" in data:
            self.products = data["products"]
        else:
            pytest.fail("dataset_manifest.json must be a JSON array or object with 'products' key")

    def test_manifest_has_minimum_product_count(self):
        assert len(self.products) >= 10, (
            f"Manifest has {len(self.products)} products; Phase 0 requires >= 10 real motors"
        )

    def test_all_products_have_product_id(self):
        for i, p in enumerate(self.products):
            assert "product_id" in p, f"Product at index {i} missing 'product_id'"
            assert p["product_id"], f"Product at index {i} has empty 'product_id'"

    def test_all_products_have_manufacturer(self):
        for p in self.products:
            assert "manufacturer" in p, f"{p.get('product_id', '?')} missing 'manufacturer'"

    def test_all_products_have_model(self):
        for p in self.products:
            assert "model" in p, f"{p.get('product_id', '?')} missing 'model'"

    def test_all_products_have_source_status(self):
        for p in self.products:
            assert "source_status" in p, f"{p.get('product_id', '?')} missing 'source_status'"

    def test_all_products_have_pdf_reference(self):
        for p in self.products:
            assert "pdf" in p, f"{p.get('product_id', '?')} missing 'pdf' block"

    def test_all_products_have_web_reference(self):
        for p in self.products:
            assert "web" in p, f"{p.get('product_id', '?')} missing 'web' block"

    def test_all_products_have_csv_reference(self):
        for p in self.products:
            assert "csv" in p, f"{p.get('product_id', '?')} missing 'csv' block"

    def test_unique_product_ids(self):
        ids = [p["product_id"] for p in self.products]
        assert len(ids) == len(set(ids)), "Duplicate product_id values found in manifest"

    def test_pdf_file_exists(self):
        """The referenced PDF must exist on disk."""
        for p in self.products:
            pdf_rel = p.get("pdf", {}).get("file", "")
            if pdf_rel:
                pdf_path = DATA_DIR / pdf_rel
                assert pdf_path.exists(), f"PDF file missing for {p['product_id']}: {pdf_rel}"

    def test_csv_file_exists(self):
        """The referenced CSV must exist on disk."""
        for p in self.products:
            csv_rel = p.get("csv", {}).get("file", "")
            if csv_rel:
                csv_path = DATA_DIR / csv_rel
                assert csv_path.exists(), f"CSV file missing for {p['product_id']}: {csv_rel}"

    def test_web_url_files_exist(self):
        """Web URL reference files must exist on disk."""
        for p in self.products:
            web_rel = p.get("web", {}).get("file", "")
            if web_rel:
                web_path = DATA_DIR / web_rel
                assert web_path.exists(), f"Web URL file missing for {p['product_id']}: {web_rel}"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_config_loads(self):
        from productiq.config import load_config
        config = load_config()
        assert config is not None

    def test_config_has_llm_key_attribute(self):
        from productiq.config import load_config
        config = load_config()
        # has_llm_key property must exist; we don't assert it's True here
        # (key may not be configured in CI)
        assert hasattr(config, "has_llm_key")

    def test_config_has_data_dir(self):
        from productiq.config import load_config
        config = load_config()
        assert config.data_dir
        assert os.path.isdir(config.data_dir), f"Config data_dir does not exist: {config.data_dir}"

    def test_env_example_has_llm_key_placeholder(self):
        env_example = PROJECT_ROOT / ".env.example"
        assert env_example.exists(), ".env.example is missing"
        content = env_example.read_text(encoding="utf-8")
        assert "LLM_API_KEY" in content, ".env.example must contain LLM_API_KEY placeholder"
