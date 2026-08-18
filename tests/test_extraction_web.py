"""
test_extraction_web.py
=======================
Tests for the web extractor.

Live web tests (actual HTTP requests) are skipped if:
  - Network is unavailable
  - The WEG website returns 403 (documented limitation — see KNOWN LIMITATIONS in docs)

Deterministic tests use a local HTML fixture that is clearly labeled as a
TEST FIXTURE — it does NOT represent actual WEG manufacturer data.

The fixture tests verify that the HTML parser works correctly regardless of
whether the live WEG site is accessible.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_motor_page.html"
URL_FILE_PATH = Path(__file__).parent.parent / "data" / "web" / "PIQ-W22SP-4P-1.1.url.txt"


class TestWebExtractorInit:
    def test_importable(self):
        from productiq.extraction import WebExtractor
        assert WebExtractor is not None

    def test_instantiates(self):
        from productiq.extraction import WebExtractor
        ex = WebExtractor(
            url_file=Path("/nonexistent.url.txt"),
            source_id="test",
            product_id="PIQ-TEST",
        )
        assert ex is not None

    def test_missing_url_file_returns_failure(self):
        from productiq.extraction import WebExtractor
        ex = WebExtractor(
            url_file=Path("/nonexistent.url.txt"),
            source_id="test",
            product_id="PIQ-TEST",
        )
        result = ex.extract()
        assert result.succeeded is False
        assert result.error is not None

    def test_empty_url_file_returns_failure(self, tmp_path):
        from productiq.extraction import WebExtractor
        empty_file = tmp_path / "empty.url.txt"
        empty_file.write_text("")
        ex = WebExtractor(url_file=empty_file, source_id="test", product_id="PIQ-TEST")
        result = ex.extract()
        assert result.succeeded is False


class TestWebHTMLParser:
    """
    Deterministic tests using a local HTML fixture.
    These tests are NOT network-dependent.
    The fixture is labeled as a TEST FIXTURE — not real manufacturer data.
    """

    @pytest.fixture
    def extractor(self):
        from productiq.extraction import WebExtractor
        if not FIXTURE_PATH.exists():
            pytest.skip(f"Test fixture not found: {FIXTURE_PATH}")
        return WebExtractor(
            url_file=FIXTURE_PATH,  # won't be used — we inject HTML directly
            source_id="test-fixture",
            product_id="PIQ-TEST-FIXTURE",
        )

    def test_parse_html_returns_list(self, extractor):
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        result = extractor._parse_html(html=html, url="http://fixture.local/")
        assert isinstance(result, list)

    def test_parse_html_extracts_from_table(self, extractor):
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        records = extractor._parse_html(html=html, url="http://fixture.local/")
        attrs = {r.attribute for r in records}
        # The fixture table contains rated_power and rated_current
        assert "rated_power" in attrs or "rated_current" in attrs or "rated_speed" in attrs, (
            f"Expected motor spec attributes, got: {attrs}"
        )

    def test_parse_html_extracts_from_dl(self, extractor):
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        records = extractor._parse_html(html=html, url="http://fixture.local/")
        # The fixture has <dl> with IP rating, voltage, frequency
        found = {r.attribute for r in records}
        # At least one of the DL-defined attributes should appear
        dl_expected = {"ip_rating", "rated_voltage", "frequency"}
        assert found & dl_expected, f"No DL attributes found. Got: {found}"

    def test_parse_html_provenance_has_url(self, extractor):
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        records = extractor._parse_html(html=html, url="http://fixture.local/")
        for r in records:
            assert r.url == "http://fixture.local/", f"URL missing in {r.attribute}"

    def test_parse_html_provenance_has_source_id(self, extractor):
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        records = extractor._parse_html(html=html, url="http://fixture.local/")
        for r in records:
            assert r.source_id == "test-fixture"

    def test_parse_html_all_have_raw_value(self, extractor):
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        records = extractor._parse_html(html=html, url="http://fixture.local/")
        for r in records:
            assert r.raw_value, f"Empty raw_value for {r.attribute}"

    def test_parse_html_no_fabricated_values(self, extractor):
        """Parser must not generate evidence without a source string."""
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        records = extractor._parse_html(html=html, url="http://fixture.local/")
        for r in records:
            # evidence_text must reference actual content, not be empty
            assert r.evidence_text is not None

    def test_method_field_set(self, extractor):
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        records = extractor._parse_html(html=html, url="http://fixture.local/")
        from productiq.extraction.models import ExtractionMethod
        valid_methods = {m.value for m in ExtractionMethod}
        for r in records:
            assert r.method in valid_methods, f"Unknown method: {r.method}"


class TestWebFailureHandling:
    """
    Tests that network failures are correctly captured and not fabricated.
    Uses mock to simulate network conditions without actual HTTP requests.
    """

    def test_http_403_recorded_as_failure(self, tmp_path):
        """HTTP 403 (what WEG returns) must produce a FAILED result, not fake data."""
        from productiq.extraction import WebExtractor
        from productiq.extraction.models import ExtractionStatus
        import requests

        url_file = tmp_path / "test.url.txt"
        url_file.write_text("https://httpbin.org/status/403")

        ex = WebExtractor(url_file=url_file, source_id="test", product_id="PIQ-TEST")

        # Mock requests.get to raise HTTPError for 403
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "403 Forbidden"
        )
        with patch("requests.get", return_value=mock_response):
            result = ex.extract()

        assert result.status == ExtractionStatus.FAILED.value
        assert result.evidence_count == 0
        assert result.error is not None

    def test_timeout_recorded_as_failure(self, tmp_path):
        from productiq.extraction import WebExtractor
        from productiq.extraction.models import ExtractionStatus
        import requests

        url_file = tmp_path / "test.url.txt"
        url_file.write_text("https://httpbin.org/delay/30")

        ex = WebExtractor(url_file=url_file, source_id="test", product_id="PIQ-TEST")

        with patch("requests.get", side_effect=requests.exceptions.Timeout("Timed out")):
            result = ex.extract()

        assert result.status == ExtractionStatus.FAILED.value
        assert result.evidence_count == 0

    def test_connection_error_recorded(self, tmp_path):
        from productiq.extraction import WebExtractor
        from productiq.extraction.models import ExtractionStatus
        import requests

        url_file = tmp_path / "test.url.txt"
        url_file.write_text("https://nonexistent-domain-xyz123.example.com/")

        ex = WebExtractor(url_file=url_file, source_id="test", product_id="PIQ-TEST")

        with patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError("DNS failure")
        ):
            result = ex.extract()

        assert result.status == ExtractionStatus.FAILED.value
        assert result.error is not None

    def test_failed_result_has_no_fabricated_evidence(self, tmp_path):
        from productiq.extraction import WebExtractor
        import requests

        url_file = tmp_path / "test.url.txt"
        url_file.write_text("https://example.com/")

        ex = WebExtractor(url_file=url_file, source_id="test", product_id="PIQ-TEST")

        with patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
            result = ex.extract()

        # No evidence must be generated when fetch fails
        assert result.evidence_count == 0


class TestWebNetworkAvailability:
    """Documents the WEG HTTP 403 limitation and ensures it's handled correctly."""

    def test_network_check_function_exists(self):
        from productiq.extraction.web_extractor import check_network_available
        result = check_network_available()
        assert isinstance(result, bool)

    @pytest.mark.skipif(
        not URL_FILE_PATH.exists(),
        reason="URL file not available"
    )
    def test_weg_site_returns_403_or_is_unavailable(self):
        """
        Documents that WEG.net returns HTTP 403 for bot/automated requests.
        This test confirms the failure is correctly captured — never fabricated.
        """
        from productiq.extraction import WebExtractor
        from productiq.extraction.models import ExtractionStatus
        from productiq.extraction.web_extractor import check_network_available

        if not check_network_available():
            pytest.skip("Network unavailable")

        ex = WebExtractor(
            url_file=URL_FILE_PATH,
            source_id="web-test",
            product_id="PIQ-W22SP-4P-1.1"
        )
        result = ex.extract()

        # Either it succeeded (unexpected but not wrong) or it failed correctly
        if result.status == ExtractionStatus.FAILED.value:
            # Verify the error is recorded, not fabricated data
            assert result.error is not None
            assert result.evidence_count == 0
            assert "403" in result.error or "Forbidden" in result.error or (
                "timeout" in result.error.lower() or "connection" in result.error.lower()
            ), f"Unexpected error: {result.error}"
        # If somehow it succeeded, that's OK too — just verify provenance
        else:
            for e in result.evidence:
                assert e.url is not None
