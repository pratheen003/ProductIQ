"""
test_schema.py
==============
Unit tests for the ProductIQ canonical motor schema.

Tests:
- DataStatus enum has exactly four members and correct values
- FieldValue rejects invalid status values at instantiation
- FieldValue accepts all four valid status values
- FieldValue with status=Unknown enforces value=None
- FieldValue with status=Verified requires at least one source
- MotorProduct instantiates with all-Unknown fields (clean slate)
- MotorProduct with a populated Verified field round-trips through JSON
- MotorProduct serializes to JSON cleanly
- MotorProduct deserializes from JSON cleanly
- CANONICAL_UNITS covers all 11 technical fields
- MotorProduct.technical_fields returns exactly 11 fields
"""
import json
import pytest
from pydantic import ValidationError

from productiq.schema import (
    CANONICAL_UNITS,
    DataStatus,
    FieldValue,
    MotorProduct,
    SourceEntry,
    SourceType,
)


# ---------------------------------------------------------------------------
# DataStatus enum
# ---------------------------------------------------------------------------

class TestDataStatus:
    def test_has_exactly_four_members(self):
        assert len(DataStatus) == 4

    def test_correct_values(self):
        assert DataStatus.VERIFIED.value == "Verified"
        assert DataStatus.INFERRED.value == "Inferred"
        assert DataStatus.CONFLICTED.value == "Conflicted"
        assert DataStatus.UNKNOWN.value == "Unknown"

    def test_enum_from_string(self):
        assert DataStatus("Verified") == DataStatus.VERIFIED
        assert DataStatus("Inferred") == DataStatus.INFERRED
        assert DataStatus("Conflicted") == DataStatus.CONFLICTED
        assert DataStatus("Unknown") == DataStatus.UNKNOWN

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            DataStatus("Fake")

    def test_invalid_string_raises_guessed(self):
        with pytest.raises(ValueError):
            DataStatus("verified")  # Case sensitive


# ---------------------------------------------------------------------------
# FieldValue
# ---------------------------------------------------------------------------

class TestFieldValue:
    def test_default_is_unknown(self):
        fv = FieldValue()
        assert fv.status == DataStatus.UNKNOWN
        assert fv.value is None
        assert fv.confidence is None
        assert fv.sources == []

    def test_valid_status_verified(self):
        src = SourceEntry(
            source_id="test-src",
            source_type=SourceType.PDF,
            location="p.1",
            reference="https://example.com/doc.pdf",
        )
        fv = FieldValue(value=1.1, unit="kW", status=DataStatus.VERIFIED, confidence=0.95, sources=[src])
        assert fv.status == DataStatus.VERIFIED
        assert fv.value == 1.1

    def test_valid_status_inferred(self):
        src = SourceEntry(
            source_id="test-src",
            source_type=SourceType.CSV,
            location="row 1",
            reference="/data/csv/legacy.csv",
        )
        fv = FieldValue(value=50, unit="Hz", status=DataStatus.INFERRED, confidence=0.7, sources=[src])
        assert fv.status == DataStatus.INFERRED

    def test_valid_status_conflicted(self):
        fv = FieldValue(value=None, unit="kW", status=DataStatus.CONFLICTED, confidence=None, sources=[])
        assert fv.status == DataStatus.CONFLICTED

    def test_valid_status_unknown(self):
        fv = FieldValue(value=None, unit="rpm", status=DataStatus.UNKNOWN)
        assert fv.status == DataStatus.UNKNOWN

    def test_invalid_status_string_raises(self):
        with pytest.raises(ValidationError):
            FieldValue(status="INVALID_STATUS")

    def test_invalid_status_random_raises(self):
        with pytest.raises(ValidationError):
            FieldValue(status="Guessed")

    def test_unknown_with_value_raises(self):
        """Unknown status must have value=None — no guessing."""
        with pytest.raises(ValidationError):
            FieldValue(value=42.0, unit="kW", status=DataStatus.UNKNOWN)

    def test_verified_without_sources_raises(self):
        """Verified fields must cite at least one source."""
        with pytest.raises(ValidationError):
            FieldValue(value=1.1, unit="kW", status=DataStatus.VERIFIED, confidence=0.9, sources=[])

    def test_inferred_without_sources_raises(self):
        """Inferred fields must cite at least one source."""
        with pytest.raises(ValidationError):
            FieldValue(value=1.1, unit="kW", status=DataStatus.INFERRED, confidence=0.7, sources=[])

    def test_confidence_bounds(self):
        """Confidence must be in [0.0, 1.0]."""
        with pytest.raises(ValidationError):
            FieldValue(confidence=1.5)
        with pytest.raises(ValidationError):
            FieldValue(confidence=-0.1)

    def test_multiple_sources_allowed(self):
        """A field must be able to hold multiple source entries."""
        src1 = SourceEntry(source_id="s1", source_type=SourceType.PDF, location="p.1", reference="a.pdf")
        src2 = SourceEntry(source_id="s2", source_type=SourceType.WEB, location="table", reference="https://x.com")
        fv = FieldValue(
            value=1.1,
            unit="kW",
            status=DataStatus.CONFLICTED,
            confidence=None,
            sources=[src1, src2],
        )
        assert len(fv.sources) == 2


# ---------------------------------------------------------------------------
# SourceEntry
# ---------------------------------------------------------------------------

class TestSourceEntry:
    def test_valid_pdf_source(self):
        src = SourceEntry(
            source_id="weg-brochure",
            source_type=SourceType.PDF,
            location="p.5, row 1",
            reference="https://static.weg.net/doc.pdf",
        )
        assert src.source_type == SourceType.PDF

    def test_invalid_source_type_raises(self):
        with pytest.raises(ValidationError):
            SourceEntry(
                source_id="x",
                source_type="ftp",   # not in enum
                location="x",
                reference="x",
            )


# ---------------------------------------------------------------------------
# MotorProduct
# ---------------------------------------------------------------------------

class TestMotorProduct:
    def _minimal_product(self) -> MotorProduct:
        return MotorProduct(
            product_id="PIQ-TEST-001",
            manufacturer="TestCo",
            model="Test Motor 1kW",
        )

    def test_instantiates_with_defaults(self):
        p = self._minimal_product()
        assert p.product_id == "PIQ-TEST-001"
        assert p.rated_power.status == DataStatus.UNKNOWN
        assert p.rated_power.value is None

    def test_all_technical_fields_present(self):
        p = self._minimal_product()
        fields = p.technical_fields
        expected = {
            "rated_power", "rated_voltage", "rated_current", "frequency",
            "rated_speed", "poles", "efficiency", "power_factor",
            "weight", "ip_rating", "frame_size",
        }
        assert set(fields.keys()) == expected
        assert len(fields) == 11

    def test_all_technical_fields_default_unknown(self):
        p = self._minimal_product()
        for name, fv in p.technical_fields.items():
            assert fv.status == DataStatus.UNKNOWN, f"Field '{name}' should default to Unknown"

    def test_known_field_count_zero_for_empty(self):
        p = self._minimal_product()
        assert p.known_field_count == 0

    def test_with_verified_rated_power(self):
        src = SourceEntry(
            source_id="weg-w22sp-brochure",
            source_type=SourceType.PDF,
            location="p.5, 4-pole row 1.1 kW",
            reference="https://static.weg.net/medias/downloadcenter/hf9/hd0/WEG-w22-severe-process-european-market-50058022-brochure-english-web.pdf",
        )
        p = MotorProduct(
            product_id="PIQ-W22SP-4P-1.1",
            manufacturer="WEG",
            model="W22 Severe Process IE3 (4-pole)",
            rated_power=FieldValue(
                value=1.1,
                unit="kW",
                status=DataStatus.VERIFIED,
                confidence=0.98,
                sources=[src],
            ),
        )
        assert p.rated_power.value == 1.1
        assert p.rated_power.status == DataStatus.VERIFIED
        assert p.known_field_count == 1

    def test_json_serialization_round_trip(self):
        src = SourceEntry(
            source_id="test-src",
            source_type=SourceType.CSV,
            location="row 1",
            reference="/data/legacy.csv",
        )
        p = MotorProduct(
            product_id="PIQ-RT-001",
            manufacturer="TestCo",
            model="RT Motor",
            rated_power=FieldValue(
                value=5.5,
                unit="kW",
                status=DataStatus.INFERRED,
                confidence=0.8,
                sources=[src],
            ),
        )
        json_str = p.to_json()
        # Validate it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["product_id"] == "PIQ-RT-001"
        assert parsed["rated_power"]["value"] == 5.5
        assert parsed["rated_power"]["status"] == "Inferred"
        assert len(parsed["rated_power"]["sources"]) == 1

        # Round-trip: deserialize and re-check
        p2 = MotorProduct.from_json(json_str)
        assert p2.product_id == p.product_id
        assert p2.rated_power.value == p.rated_power.value
        assert p2.rated_power.status == DataStatus.INFERRED
        assert p2.rated_power.sources[0].source_id == "test-src"

    def test_schema_version_present(self):
        p = self._minimal_product()
        assert p.schema_version == "0.1.0-phase0"

    def test_product_type_default(self):
        p = self._minimal_product()
        assert p.product_type == "three_phase_induction_motor"


# ---------------------------------------------------------------------------
# Canonical Units Registry
# ---------------------------------------------------------------------------

class TestCanonicalUnits:
    REQUIRED_FIELDS = [
        "rated_power", "rated_voltage", "rated_current", "frequency",
        "rated_speed", "poles", "efficiency", "power_factor",
        "weight", "ip_rating", "frame_size",
    ]

    def test_all_required_fields_present(self):
        for field in self.REQUIRED_FIELDS:
            assert field in CANONICAL_UNITS, f"CANONICAL_UNITS missing field: '{field}'"

    def test_specific_units(self):
        assert CANONICAL_UNITS["rated_power"] == "kW"
        assert CANONICAL_UNITS["rated_voltage"] == "V"
        assert CANONICAL_UNITS["rated_current"] == "A"
        assert CANONICAL_UNITS["frequency"] == "Hz"
        assert CANONICAL_UNITS["rated_speed"] == "rpm"
        assert CANONICAL_UNITS["efficiency"] == "%"
        assert CANONICAL_UNITS["weight"] == "kg"

    def test_dimensionless_fields_are_none(self):
        """Dimensionless fields should have unit=None."""
        assert CANONICAL_UNITS["poles"] is None
        assert CANONICAL_UNITS["power_factor"] is None
        assert CANONICAL_UNITS["ip_rating"] is None
        assert CANONICAL_UNITS["frame_size"] is None

    def test_count_is_eleven(self):
        assert len(CANONICAL_UNITS) == 11
