"""
ProductIQ Catalog Foundation Test Suite — Unilog Pipeline (Strict Ground Truth Verified)
========================================================================================
Tests input dataset ingestion, ground truth mapping, UOM normalization,
decimal fraction lookups, placeholder filtering, and FastAPI sanity endpoints.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from productiq_catalog.schema import (
    CatalogTrustStatus,
    CatalogField,
    CatalogAttributeTriple,
    CatalogInputRow,
    CatalogProduct,
)
from productiq_catalog.lookups import (
    is_placeholder,
    clean_string,
    DecimalFractionLookup,
    UOMLookup,
    ManufacturerBrandLookup,
)
from productiq_catalog.extraction import InputDatasetLoader
from productiq_catalog.ground_truth import GroundTruthStore
from productiq.api.app import app


client = TestClient(app)


class TestInputIngestion:
    """Test 1,000-row sample dataset ingestion."""

    def test_input_dataset_loads_all_rows(self):
        loader = InputDatasetLoader()
        assert loader.count() == 1000, f"Expected 1000 rows, got {loader.count()}"

    def test_input_row_columns_and_clean_data(self):
        loader = InputDatasetLoader()
        row = loader.get_by_row_id(1)
        assert row is not None
        assert row.mfg_part_num == "DCB518ASTS06G"
        assert "Diablo" in row.part_desc
        # Placeholders should be cleaned to None
        assert row.e1_brand is None
        assert row.unilog_brand is None
        assert row.dib_brand is None
        assert row.part_manuf == "Freud Inc (2435)"

    def test_lookup_by_part_number(self):
        loader = InputDatasetLoader()
        row = loader.get_by_part_num("49-94-0013")
        assert row is not None
        assert row.row_id == 17
        assert "Milwaukee" in (row.part_manuf or "")


class TestGroundTruthIngestion:
    """Test 200-item expected delivery format benchmark ingestion."""

    def test_ground_truth_loads(self):
        store = GroundTruthStore()
        assert store.count() >= 2
        rec = store.get_by_row_id(1)
        assert rec is not None
        assert rec.mfg_part_num == "PDSH4816AF"
        assert rec.expected_manufacturer == "Rheem Manufacturing"
        assert "FRIGIDAIRE" in rec.expected_brand
        assert rec.expected_product_name == "Dishwasher"
        assert len(rec.expected_attributes) >= 5

    def test_ground_truth_attributes_extraction(self):
        store = GroundTruthStore()
        rec = store.get_by_part_num("WDTS7024RZ")
        assert rec is not None
        assert rec.expected_manufacturer == "Whirlpool Corporation"
        assert "Whirlpool" in rec.expected_brand
        labels = [a.label for a in rec.expected_attributes]
        assert "Series" in labels
        assert "Voltage Rating" in labels
        assert "Amperage Rating" in labels


class TestLookupsAndNormalization:
    """Test manufacturer/brand dictionary, UOM standards, and decimal fractions."""

    def test_placeholder_filtering(self):
        assert is_placeholder("-- Unbranded --") is True
        assert is_placeholder("-- No Unilog Brand --") is True
        assert is_placeholder("-- No DIB Brand --") is True
        assert is_placeholder("-") is True
        assert is_placeholder("COMMODITY - UNBRANDED") is True
        assert is_placeholder("None") is True
        assert is_placeholder("") is True
        assert is_placeholder("DEWALT") is False
        assert is_placeholder("Milwaukee Tool") is False

        assert clean_string("-- Unbranded --") is None
        assert clean_string("  Diablo  ") == "Diablo"

    def test_manufacturer_brand_resolution(self):
        lookup = ManufacturerBrandLookup()
        # Strictly derived from ground truth (2 verified manufacturer entries)
        assert len(lookup.get_all_mappings()) == 2

        # Exact match on verified ground truth entry (PDSH4816AF -> Rheem Manufacturing / FRIGIDAIRE®)
        res1 = lookup.resolve(
            part_manuf="Appliance Dealers Cooperative (APPDE)",
            part_desc="PDSH4816AF Dishwasher SS",
            mfg_part_num="PDSH4816AF",
        )
        assert res1["manufacturer"] == "Rheem Manufacturing"
        assert "FRIGIDAIRE" in res1["brand"]
        assert res1["status"] == "Verified"

        # Exact match on verified ground truth entry (WDTS7024RZ -> Whirlpool Corporation / Whirlpool®)
        res2 = lookup.resolve(
            part_manuf="Appliance Dealers Cooperative (APPDE)",
            part_desc="WDTS7024RZ Dishwasher SS",
            mfg_part_num="WDTS7024RZ",
        )
        assert res2["manufacturer"] == "Whirlpool Corporation"
        assert "Whirlpool" in res2["brand"]
        assert res2["status"] == "Verified"

        # Unverified entry outside ground truth correctly resolves to Unknown (No Fabrication Discipline)
        res_unknown = lookup.resolve(
            part_manuf="Unknown Supplier XYZ (9999)",
            part_desc="Random Tool 123",
            mfg_part_num="XYZ-999",
        )
        assert res_unknown["status"] == "Unknown"
        assert res_unknown["manufacturer"] is None
        assert res_unknown["brand"] is None
        assert res_unknown["confidence"] == 0.0

    def test_uom_standards_normalization(self):
        uom_lookup = UOMLookup()
        # Strictly verified units from ground truth
        assert uom_lookup.normalize('"') == "in"
        assert uom_lookup.normalize("in.") == "in"
        assert uom_lookup.normalize("IN") == "in"
        assert uom_lookup.normalize("in") == "in"
        assert uom_lookup.normalize("V") == "V"
        assert uom_lookup.normalize("A") == "A"
        assert uom_lookup.normalize("dBA") == "dBA"
        assert uom_lookup.normalize("DBA") == "dBA"
        assert uom_lookup.normalize("-- No UOM --") is None
        # Unverified unit outside ground truth returns None
        assert uom_lookup.normalize("furlongs") is None

    def test_decimal_fraction_table_all_63_entries(self):
        frac_lookup = DecimalFractionLookup()
        entries = frac_lookup.get_all_entries()
        assert len(entries) == 63, f"Expected 63 fraction entries, got {len(entries)}"

        # Verify key mathematical conversions
        assert frac_lookup.parse_fraction("1/64") == 0.015625
        assert frac_lookup.parse_fraction("1/2") == 0.5
        assert frac_lookup.parse_fraction("7/64") == 0.109375
        assert frac_lookup.parse_fraction("63/64") == 0.984375

        # Compound fractions
        assert frac_lookup.parse_fraction("1-1/2") == 1.5
        assert frac_lookup.parse_fraction('7-1/4"') == 7.25
        assert frac_lookup.parse_fraction("4 1/2") == 4.5
        assert frac_lookup.parse_fraction(".045") == 0.045


class TestCatalogSchemaModels:
    """Test strongly-typed scoped catalog schema models."""

    def test_catalog_field_nested_structure(self):
        field = CatalogField[str](
            value="Rheem Manufacturing",
            status=CatalogTrustStatus.VERIFIED,
            confidence=1.0,
            sources=["Part_Manuf='Appliance Dealers Cooperative (APPDE)'"],
            reason="Exact match from ground truth verified table.",
        )
        d = field.to_dict()
        assert d["value"] == "Rheem Manufacturing"
        assert d["status"] == "Verified"
        assert d["confidence"] == 1.0
        assert len(d["sources"]) == 1

    def test_catalog_product_structure(self):
        raw_in = CatalogInputRow(
            row_id=1,
            mfg_part_num="PDSH4816AF",
            part_desc="PDSH4816AF Dishwasher SS - Display Only",
            part_manuf="Appliance Dealers Cooperative (APPDE)",
        )
        product = CatalogProduct(
            row_id=1,
            mfg_part_num="PDSH4816AF",
            part_desc=raw_in.part_desc,
            raw_input=raw_in,
            manufacturer_name=CatalogField[str](value="Rheem Manufacturing", status=CatalogTrustStatus.VERIFIED),
            brand_name=CatalogField[str](value="FRIGIDAIRE®", status=CatalogTrustStatus.VERIFIED),
            product_name=CatalogField[str](value="Dishwasher", status=CatalogTrustStatus.VERIFIED),
        )
        pdict = product.to_dict()
        assert pdict["row_id"] == 1
        assert pdict["manufacturer_name"]["value"] == "Rheem Manufacturing"
        assert pdict["brand_name"]["value"] == "FRIGIDAIRE®"


class TestCatalogAPIRoutes:
    """Test live FastAPI endpoints mounted under /api/catalog/*."""

    def test_catalog_health_endpoint(self):
        resp = client.get("/api/catalog/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["input_rows_loaded"] == 1000
        assert data["ground_truth_rows_loaded"] >= 2
        assert data["decimal_fractions_loaded"] == 63
        assert data["manufacturer_mappings_loaded"] == 2

    def test_catalog_lookups_manufacturers(self):
        resp = client.get("/api/catalog/lookups/manufacturers?query=PDSH4816AF")
        assert resp.status_code == 200
        data = resp.json()
        assert data["matched"] is True
        assert data["result"]["manufacturer"] == "Rheem Manufacturing"
        assert "FRIGIDAIRE" in data["result"]["brand"]

    def test_catalog_lookups_uom(self):
        resp = client.get("/api/catalog/lookups/uom?alias=IN")
        assert resp.status_code == 200
        data = resp.json()
        assert data["canonical_uom"] == "in"

    def test_catalog_lookups_fractions(self):
        resp = client.get("/api/catalog/lookups/fractions?fraction=7-1/4")
        assert resp.status_code == 200
        data = resp.json()
        assert data["decimal"] == 7.25

    def test_catalog_input_row_endpoint(self):
        resp = client.get("/api/catalog/input/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_id"] == 1
        assert data["mfg_part_num"] == "DCB518ASTS06G"

    def test_catalog_ground_truth_endpoint(self):
        resp = client.get("/api/catalog/ground-truth/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_id"] == 1
        assert data["mfg_part_num"] == "PDSH4816AF"
        assert "FRIGIDAIRE" in data["expected_brand"]
