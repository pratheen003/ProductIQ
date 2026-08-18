"""
test_normalization_values.py
=============================
Unit tests for the Phase 2 value parser.

Covers:
- Numeric + unit string parsing
- Plain numeric string parsing
- IP rating extraction from various formats
- Frame size passthrough
- Pole count parsing
- Malformed input → ValueParseError (never fabricated value)
- Edge cases: empty strings, whitespace, mixed case
"""
import pytest
from productiq.normalization.value_parser import (
    ValueParseError,
    parse_frame_size,
    parse_ip_rating,
    parse_numeric,
    parse_poles,
    parse_string_field,
    safe_parse_float,
)


class TestParseNumeric:
    """Test parse_numeric with various real-world value strings."""

    def test_plain_float(self):
        val, unit = parse_numeric("1.1")
        assert abs(val - 1.1) < 1e-9
        assert unit is None

    def test_plain_int(self):
        val, unit = parse_numeric("1455")
        assert abs(val - 1455.0) < 1e-9

    def test_float_with_kw(self):
        val, unit = parse_numeric("1.1 kW")
        assert abs(val - 1.1) < 1e-9
        assert unit == "kW"

    def test_float_with_percent(self):
        val, unit = parse_numeric("84.8 %")
        assert abs(val - 84.8) < 1e-9
        assert unit == "%"

    def test_float_with_percent_nospace(self):
        val, unit = parse_numeric("84.8%")
        assert abs(val - 84.8) < 1e-9
        assert unit == "%"

    def test_kg_value(self):
        val, unit = parse_numeric("19.5 kg")
        assert abs(val - 19.5) < 1e-9
        assert unit == "kg"

    def test_voltage(self):
        val, unit = parse_numeric("400 V")
        assert abs(val - 400.0) < 1e-9
        assert unit == "V"

    def test_rpm_value(self):
        val, unit = parse_numeric("1455 rpm")
        assert abs(val - 1455.0) < 1e-9
        assert unit == "rpm"

    def test_power_factor_fraction(self):
        val, unit = parse_numeric("0.80")
        assert abs(val - 0.80) < 1e-9

    def test_current_value(self):
        val, unit = parse_numeric("2.34 A")
        assert abs(val - 2.34) < 1e-9
        assert unit == "A"

    def test_whitespace_stripped(self):
        val, unit = parse_numeric("  1.1  ")
        assert abs(val - 1.1) < 1e-9

    def test_scientific_notation(self):
        val, unit = parse_numeric("1.1e3")
        assert abs(val - 1100.0) < 1e-6

    def test_empty_string_raises(self):
        with pytest.raises(ValueParseError):
            parse_numeric("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueParseError):
            parse_numeric("   ")

    def test_non_numeric_raises(self):
        with pytest.raises(ValueParseError):
            parse_numeric("abc kW")

    def test_none_raises(self):
        with pytest.raises(ValueParseError):
            parse_numeric(None)  # type: ignore

    def test_hp_value(self):
        val, unit = parse_numeric("1.5 HP")
        assert abs(val - 1.5) < 1e-9
        assert unit == "HP"


class TestParseIPRating:
    """Test IP rating extraction."""

    def test_ip55_exact(self):
        assert parse_ip_rating("IP55") == "IP55"

    def test_ip56_exact(self):
        assert parse_ip_rating("IP56") == "IP56"

    def test_ip_lowercase(self):
        assert parse_ip_rating("ip56") == "IP56"

    def test_ip_with_space(self):
        assert parse_ip_rating("IP 56") == "IP56"

    def test_bare_number(self):
        assert parse_ip_rating("56") == "IP56"

    def test_ip_with_description(self):
        # Long note from CSV
        result = parse_ip_rating("IP56+ sealing described; standard table does not list IP as a field")
        assert result == "IP56"

    def test_empty_passthrough(self):
        # Empty strings are returned as-is (caller should handle)
        assert parse_ip_rating("") == ""


class TestParseFrameSize:
    """Test frame size passthrough."""

    def test_90s_frame(self):
        assert parse_frame_size("90S") == "90S"

    def test_l90s_frame(self):
        assert parse_frame_size("L90S") == "L90S"

    def test_132m_frame(self):
        assert parse_frame_size("132M") == "132M"

    def test_stripped(self):
        assert parse_frame_size("  90S  ") == "90S"

    def test_empty_returns_empty(self):
        assert parse_frame_size("") == ""


class TestParsePoles:
    """Test pole count parsing."""

    def test_bare_4(self):
        assert parse_poles("4") == 4

    def test_bare_6(self):
        assert parse_poles("6") == 6

    def test_4_poles(self):
        assert parse_poles("4 poles") == 4

    def test_4_pole(self):
        assert parse_poles("4-pole") == 4

    def test_invalid_raises(self):
        with pytest.raises(ValueParseError):
            parse_poles("four")


class TestParseStringField:
    """Test parse_string_field."""

    def test_basic_string(self):
        assert parse_string_field("IP56") == "IP56"

    def test_stripped(self):
        assert parse_string_field("  IP56  ") == "IP56"

    def test_empty_raises(self):
        with pytest.raises(ValueParseError):
            parse_string_field("")

    def test_non_string_raises(self):
        with pytest.raises(ValueParseError):
            parse_string_field(123)  # type: ignore


class TestSafeParseFloat:
    """Test safe_parse_float convenience wrapper."""

    def test_plain_number(self):
        assert abs(safe_parse_float("1.1") - 1.1) < 1e-9

    def test_number_with_unit_discards_unit(self):
        # Unit is discarded (must already be in EvidenceRecord.unit)
        assert abs(safe_parse_float("1.1 kW") - 1.1) < 1e-9

    def test_empty_raises(self):
        with pytest.raises(ValueParseError):
            safe_parse_float("")
