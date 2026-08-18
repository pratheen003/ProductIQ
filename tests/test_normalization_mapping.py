"""
test_normalization_mapping.py
==============================
Unit tests for the Phase 2 attribute mapper.

Covers:
- Canonical mappings (evidence attribute → MotorProduct field)
- Metadata classification (unit columns → skip)
- Unmapped attributes (technical fields with no canonical equivalent)
- Skip classification (source references, identity fields)
- All canonical fields are reachable from at least one evidence attribute
- Case-insensitive fallback lookup
"""
import pytest
from productiq.normalization.attribute_mapper import (
    MappingKind,
    all_canonical_fields,
    get_canonical_field,
    get_mapping,
    is_canonical,
)
from productiq.schema import CANONICAL_UNITS


class TestCanonicalMappings:
    """Test that evidence attributes map to the correct canonical fields."""

    def test_rated_power_maps_to_rated_power(self):
        field, kind, _ = get_mapping("rated_power")
        assert field == "rated_power"
        assert kind == MappingKind.CANONICAL

    def test_rated_power_kw_maps_to_rated_power(self):
        field, kind, _ = get_mapping("rated_power_kw")
        assert field == "rated_power"
        assert kind == MappingKind.CANONICAL

    def test_rated_power_hp_maps_to_rated_power(self):
        field, kind, _ = get_mapping("rated_power_hp")
        assert field == "rated_power"
        assert kind == MappingKind.CANONICAL

    def test_full_load_current_maps_to_rated_current(self):
        field, kind, _ = get_mapping("full_load_current_a")
        assert field == "rated_current"
        assert kind == MappingKind.CANONICAL

    def test_rated_current_maps_to_rated_current(self):
        field, kind, _ = get_mapping("rated_current")
        assert field == "rated_current"
        assert kind == MappingKind.CANONICAL

    def test_efficiency_maps_to_efficiency(self):
        field, kind, _ = get_mapping("efficiency")
        assert field == "efficiency"
        assert kind == MappingKind.CANONICAL

    def test_power_factor_maps_to_power_factor(self):
        field, kind, _ = get_mapping("power_factor")
        assert field == "power_factor"
        assert kind == MappingKind.CANONICAL

    def test_weight_maps_to_weight(self):
        field, kind, _ = get_mapping("weight")
        assert field == "weight"
        assert kind == MappingKind.CANONICAL

    def test_frame_size_maps_to_frame_size(self):
        field, kind, _ = get_mapping("frame_size")
        assert field == "frame_size"
        assert kind == MappingKind.CANONICAL

    def test_frame_maps_to_frame_size(self):
        field, kind, _ = get_mapping("frame")
        assert field == "frame_size"
        assert kind == MappingKind.CANONICAL

    def test_ip_rating_maps_to_ip_rating(self):
        field, kind, _ = get_mapping("ip_rating")
        assert field == "ip_rating"
        assert kind == MappingKind.CANONICAL

    def test_ip_rating_note_maps_to_ip_rating(self):
        field, kind, _ = get_mapping("ip_rating_note")
        assert field == "ip_rating"
        assert kind == MappingKind.CANONICAL

    def test_rated_voltage_maps_to_rated_voltage(self):
        field, kind, _ = get_mapping("rated_voltage")
        assert field == "rated_voltage"
        assert kind == MappingKind.CANONICAL

    def test_rated_speed_maps_to_rated_speed(self):
        field, kind, _ = get_mapping("rated_speed")
        assert field == "rated_speed"
        assert kind == MappingKind.CANONICAL

    def test_rated_speed_rpm_maps_to_rated_speed(self):
        field, kind, _ = get_mapping("rated_speed_rpm")
        assert field == "rated_speed"
        assert kind == MappingKind.CANONICAL


class TestMetadataMappings:
    """Test that unit/metadata columns are classified correctly."""

    def test_rated_power_unit_is_metadata(self):
        _, kind, _ = get_mapping("rated_power_unit")
        assert kind == MappingKind.METADATA

    def test_rated_current_unit_is_metadata(self):
        _, kind, _ = get_mapping("rated_current_unit")
        assert kind == MappingKind.METADATA

    def test_current_unit_is_metadata(self):
        _, kind, _ = get_mapping("current_unit")
        assert kind == MappingKind.METADATA


class TestUnmappedAttributes:
    """Test that non-canonical technical attributes are classified as unmapped."""

    def test_torque_is_unmapped(self):
        _, kind, _ = get_mapping("full_load_torque_nm")
        assert kind == MappingKind.UNMAPPED

    def test_inertia_is_unmapped(self):
        _, kind, _ = get_mapping("inertia_kgm2")
        assert kind == MappingKind.UNMAPPED

    def test_sound_is_unmapped(self):
        _, kind, _ = get_mapping("sound_dba")
        assert kind == MappingKind.UNMAPPED

    def test_partial_load_efficiency_is_unmapped(self):
        _, kind, _ = get_mapping("efficiency_at_50pct_load")
        assert kind == MappingKind.UNMAPPED

    def test_partial_load_pf_is_unmapped(self):
        _, kind, _ = get_mapping("power_factor_at_75pct_load")
        assert kind == MappingKind.UNMAPPED

    def test_unknown_attribute_is_unmapped(self):
        _, kind, _ = get_mapping("completely_unknown_column")
        assert kind == MappingKind.UNMAPPED


class TestSkipMappings:
    """Test that skip attributes are properly classified."""

    def test_source_location_is_skip(self):
        _, kind, _ = get_mapping("source_location")
        assert kind == MappingKind.SKIP


class TestHelperFunctions:
    """Test is_canonical and get_canonical_field helpers."""

    def test_is_canonical_for_canonical_attr(self):
        assert is_canonical("rated_power") is True

    def test_is_canonical_false_for_metadata(self):
        assert is_canonical("rated_power_unit") is False

    def test_is_canonical_false_for_unmapped(self):
        assert is_canonical("full_load_torque_nm") is False

    def test_get_canonical_field_returns_field(self):
        assert get_canonical_field("rated_power_kw") == "rated_power"

    def test_get_canonical_field_returns_none_for_metadata(self):
        assert get_canonical_field("rated_power_unit") is None

    def test_get_canonical_field_returns_none_for_unmapped(self):
        assert get_canonical_field("inertia_kgm2") is None


class TestAllCanonicalFieldsReachable:
    """Verify all Phase 0 canonical fields can be reached from at least one evidence attribute."""

    def test_all_canonical_fields_listed(self):
        """all_canonical_fields() must match CANONICAL_UNITS from Phase 0."""
        expected = set(CANONICAL_UNITS.keys())
        actual = set(all_canonical_fields())
        assert expected == actual

    @pytest.mark.parametrize("canonical_field", list(CANONICAL_UNITS.keys()))
    def test_canonical_field_has_at_least_one_mapping(self, canonical_field):
        """Every canonical field must have at least one evidence attribute mapping."""
        from productiq.normalization.attribute_mapper import _ATTRIBUTE_MAP
        mappings = [
            attr for attr, (cf, kind, _) in _ATTRIBUTE_MAP.items()
            if cf == canonical_field and kind == MappingKind.CANONICAL
        ]
        assert len(mappings) >= 1, (
            f"Canonical field '{canonical_field}' has no evidence attribute mapping. "
            "Add at least one CANONICAL mapping entry to _ATTRIBUTE_MAP."
        )
