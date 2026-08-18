"""
test_normalization_units.py
============================
Unit tests for the Phase 2 unit converter.

Covers:
- Power conversions (W → kW, HP → kW, mW → kW, kW passthrough)
- Mass conversions (g → kg, lb → kg, kg passthrough)
- Efficiency normalization (fraction → %, % passthrough)
- Power factor normalization (% → fraction, fraction passthrough)
- Passthrough units (V, A, Hz, rpm)
- Unit alias normalization (case-insensitive, common variants)
- Equivalence checking
- Error cases (unknown units, unsupported conversions)
"""
import pytest
from productiq.normalization.unit_converter import (
    UnitConversionError,
    convert_value,
    is_equivalent,
    normalize_unit_string,
)


class TestPowerConversions:
    """Test W/HP/mW → kW conversions."""

    def test_watts_to_kw(self):
        val, unit = convert_value("rated_power", 1100.0, "W")
        assert unit == "kW"
        assert abs(val - 1.1) < 1e-6

    def test_kw_passthrough(self):
        val, unit = convert_value("rated_power", 1.1, "kW")
        assert unit == "kW"
        assert abs(val - 1.1) < 1e-6

    def test_hp_to_kw(self):
        val, unit = convert_value("rated_power", 1.5, "HP")
        assert unit == "kW"
        assert abs(val - 1.11855) < 1e-4  # 1.5 × 0.7457

    def test_hp_to_kw_2hp(self):
        val, unit = convert_value("rated_power", 2.0, "HP")
        assert unit == "kW"
        assert abs(val - 1.4914) < 1e-4

    def test_milliwatt_to_kw(self):
        val, unit = convert_value("rated_power", 1_100_000.0, "mW")
        assert unit == "kW"
        assert abs(val - 1.1) < 1e-6

    def test_unknown_power_unit_raises(self):
        with pytest.raises(UnitConversionError):
            convert_value("rated_power", 1.1, "BTU")


class TestMassConversions:
    """Test g/lb → kg conversions."""

    def test_grams_to_kg(self):
        val, unit = convert_value("weight", 19500.0, "g")
        assert unit == "kg"
        assert abs(val - 19.5) < 1e-6

    def test_kg_passthrough(self):
        val, unit = convert_value("weight", 19.5, "kg")
        assert unit == "kg"
        assert abs(val - 19.5) < 1e-6

    def test_lb_to_kg(self):
        val, unit = convert_value("weight", 1.0, "lb")
        assert unit == "kg"
        assert abs(val - 0.453592) < 1e-6

    def test_pounds_to_kg(self):
        val, unit = convert_value("weight", 43.0, "lb")
        assert unit == "kg"
        assert abs(val - 19.504456) < 1e-4

    def test_unknown_mass_unit_raises(self):
        with pytest.raises(UnitConversionError):
            convert_value("weight", 19.5, "stone")


class TestEfficiencyNormalization:
    """Test efficiency: fraction → %, % passthrough."""

    def test_percent_passthrough(self):
        val, unit = convert_value("efficiency", 84.8, "%")
        assert unit == "%"
        assert abs(val - 84.8) < 1e-6

    def test_fraction_to_percent(self):
        val, unit = convert_value("efficiency", 0.848, None)
        assert unit == "%"
        assert abs(val - 84.8) < 1e-5

    def test_high_value_stays_percent(self):
        # 83.0 should stay as 83.0 (already percentage)
        val, unit = convert_value("efficiency", 83.0, "%")
        assert abs(val - 83.0) < 1e-6

    def test_fraction_boundary(self):
        # 1.0 = 100% efficiency (fraction)
        val, unit = convert_value("efficiency", 1.0, None)
        assert unit == "%"
        assert abs(val - 100.0) < 1e-6


class TestPowerFactorNormalization:
    """Test power factor: fraction passthrough, % → fraction."""

    def test_fraction_passthrough(self):
        val, unit = convert_value("power_factor", 0.80, None)
        assert unit is None
        assert abs(val - 0.80) < 1e-6

    def test_fraction_passthrough_low(self):
        val, unit = convert_value("power_factor", 0.59, None)
        assert abs(val - 0.59) < 1e-6

    def test_percent_to_fraction(self):
        val, unit = convert_value("power_factor", 80.0, "%")
        assert unit is None
        assert abs(val - 0.80) < 1e-6


class TestPassthroughUnits:
    """Test V, A, Hz, rpm passthroughs."""

    def test_voltage_passthrough(self):
        val, unit = convert_value("rated_voltage", 400.0, "V")
        assert unit == "V"
        assert abs(val - 400.0) < 1e-6

    def test_current_passthrough(self):
        val, unit = convert_value("rated_current", 2.34, "A")
        assert unit == "A"
        assert abs(val - 2.34) < 1e-6

    def test_frequency_passthrough(self):
        val, unit = convert_value("frequency", 50.0, "Hz")
        assert unit == "Hz"
        assert abs(val - 50.0) < 1e-6

    def test_speed_passthrough(self):
        val, unit = convert_value("rated_speed", 1455.0, "rpm")
        assert unit == "rpm"
        assert abs(val - 1455.0) < 1e-6

    def test_wrong_unit_for_voltage_raises(self):
        with pytest.raises(UnitConversionError):
            convert_value("rated_voltage", 400.0, "kV")


class TestUnitAliases:
    """Test unit alias normalization (case and spelling variants)."""

    def test_kw_lowercase(self):
        assert normalize_unit_string("kw") == "kW"

    def test_kw_uppercase(self):
        assert normalize_unit_string("KW") == "kW"

    def test_hp_lowercase(self):
        assert normalize_unit_string("hp") == "HP"

    def test_horsepower(self):
        assert normalize_unit_string("horsepower") == "HP"

    def test_kg_lowercase(self):
        assert normalize_unit_string("kg") == "kg"

    def test_kilogram(self):
        assert normalize_unit_string("kilogram") == "kg"

    def test_rpm_variants(self):
        assert normalize_unit_string("rpm") == "rpm"
        assert normalize_unit_string("r/min") == "rpm"

    def test_unknown_unit_raises(self):
        with pytest.raises(UnitConversionError):
            normalize_unit_string("frobble")

    def test_none_returns_none(self):
        assert normalize_unit_string(None) is None


class TestEquivalenceCheck:
    """Test is_equivalent for conflict detection."""

    def test_same_values_equivalent(self):
        assert is_equivalent("rated_power", 1.1, "kW", 1.1, "kW") is True

    def test_floating_point_tolerance(self):
        assert is_equivalent("rated_power", 1.1, "kW", 1.1 + 1e-9, "kW") is True

    def test_different_values_not_equivalent(self):
        assert is_equivalent("rated_current", 2.34, "A", 7.22, "A") is False

    def test_none_values_both_none(self):
        assert is_equivalent("rated_power", None, "kW", None, "kW") is True

    def test_one_none_not_equivalent(self):
        assert is_equivalent("rated_power", 1.1, "kW", None, "kW") is False

    def test_different_units_not_equivalent(self):
        assert is_equivalent("weight", 19.5, "kg", 19.5, "lb") is False


class TestDeterminism:
    """Verify same input always produces same output."""

    def test_hp_conversion_deterministic(self):
        result_1, _ = convert_value("rated_power", 1.5, "HP")
        result_2, _ = convert_value("rated_power", 1.5, "HP")
        assert result_1 == result_2

    def test_watts_conversion_deterministic(self):
        result_1, _ = convert_value("rated_power", 1100.0, "W")
        result_2, _ = convert_value("rated_power", 1100.0, "W")
        assert result_1 == result_2
