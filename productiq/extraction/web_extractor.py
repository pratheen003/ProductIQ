"""
ProductIQ Web Extractor
========================
Fetches and parses manufacturer web pages to extract motor specification evidence.

Target: WEG catalog URLs referenced in data/web/*.url.txt files.
Strategy: requests HTTP fetch → BeautifulSoup HTML parse → extract tables/dl/text.

Provenance per EvidenceRecord:
  source_id, source_type="web", product_id, url, section (heading context),
  attribute, raw_value, evidence_text, method, confidence.

Critical rules:
  - Network failure is NOT a reason to fabricate data.
  - On any fetch failure: record the error, mark status=FAILED, continue.
  - Never claim successful extraction when the fetch failed.
  - Web results are lower confidence than PDF/CSV because the catalog page
    is a family-level URL, not a per-product page.
"""
from __future__ import annotations

import logging
import re
import socket
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from productiq.extraction.models import (
    EvidenceRecord,
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
)

logger = logging.getLogger("productiq.extraction.web")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEB_TIMEOUT_SECONDS = 15
WEB_USER_AGENT = (
    "ProductIQ/0.1 (research; industrial motor catalog extraction; "
    "contact: see project README)"
)

# Patterns for extracting spec values from HTML text
SPEC_PATTERNS: List[Tuple[str, str, Optional[str]]] = [
    # (regex pattern, attribute, unit)
    (r"(\d+(?:\.\d+)?)\s*kW",     "rated_power",   "kW"),
    (r"(\d+(?:\.\d+)?)\s*A\b",    "rated_current", "A"),
    (r"(\d{3,5})\s*rpm",          "rated_speed",   "rpm"),
    (r"(\d{2,3}(?:\.\d+)?)\s*%",  "efficiency",    "%"),
    (r"cos\s*[φΦ]\s*=?\s*(0\.\d+)", "power_factor", None),
    (r"(\d{2,4})\s*V\b",          "rated_voltage", "V"),
    (r"(\d{2})\s*Hz\b",           "frequency",     "Hz"),
    (r"\b(IP\s*\d{2})\b",         "ip_rating",     None),
    (r"(\d+(?:\.\d+)?)\s*kg\b",   "weight",        "kg"),
]


def _read_url_from_file(url_file: Path) -> Optional[str]:
    """Read a URL from a .url.txt file. Returns None if file is missing or empty."""
    if not url_file.exists():
        return None
    content = url_file.read_text(encoding="utf-8").strip()
    return content if content else None


def _is_network_available(host: str = "8.8.8.8", port: int = 53, timeout: int = 3) -> bool:
    """Quick DNS reachability check to detect offline environment."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


class WebExtractor:
    """
    Fetches and parses manufacturer web pages for motor specification evidence.

    Usage:
        extractor = WebExtractor(url_file, source_id, product_id)
        result = extractor.extract()  # ExtractionResult
    """

    def __init__(
        self,
        url_file: Path,
        source_id: str,
        product_id: str,
    ):
        self.url_file = url_file
        self.source_id = source_id
        self.product_id = product_id

    def extract(self) -> ExtractionResult:
        """
        Fetch and parse one web page.
        Returns ExtractionResult with evidence (may be empty) and status.
        Never fabricates data on failure.
        """
        url = _read_url_from_file(self.url_file)
        if not url:
            return ExtractionResult.failure(
                source_id=self.source_id,
                source_type="web",
                product_id=self.product_id,
                error=f"URL file not found or empty: {self.url_file}",
                source_ref=str(self.url_file),
            )

        logger.info(
            "Web extraction starting | product=%s | url=%s",
            self.product_id, url
        )

        try:
            html = self._fetch(url)
        except Exception as fetch_exc:
            error_msg = str(fetch_exc)
            logger.warning(
                "Web fetch failed | product=%s | url=%s | error=%s",
                self.product_id, url, error_msg
            )
            return ExtractionResult.failure(
                source_id=self.source_id,
                source_type="web",
                product_id=self.product_id,
                error=error_msg,
                source_ref=url,
            )

        try:
            evidence = self._parse_html(html=html, url=url)
        except Exception as parse_exc:
            logger.warning(
                "Web parse failed | product=%s | error=%s", self.product_id, parse_exc
            )
            return ExtractionResult(
                source_id=self.source_id,
                source_type="web",
                product_id=self.product_id,
                status=ExtractionStatus.PARTIAL.value,
                evidence=[],
                error=f"HTML parse error: {parse_exc}",
                source_ref=url,
            )

        status = ExtractionStatus.SUCCESS.value if evidence else ExtractionStatus.PARTIAL.value
        logger.info(
            "Web extraction complete | product=%s | evidence=%d | status=%s",
            self.product_id, len(evidence), status
        )
        return ExtractionResult(
            source_id=self.source_id,
            source_type="web",
            product_id=self.product_id,
            status=status,
            evidence=evidence,
            source_ref=url,
        )

    # ------------------------------------------------------------------
    # HTTP fetch
    # ------------------------------------------------------------------

    def _fetch(self, url: str) -> str:
        """
        Fetch HTML from a URL. Raises on any failure — caller records the error.
        Never returns fake content.
        """
        headers = {"User-Agent": WEB_USER_AGENT}
        response = requests.get(url, headers=headers, timeout=WEB_TIMEOUT_SECONDS)
        response.raise_for_status()
        logger.debug(
            "Web fetch OK | url=%s | status=%d | size=%d bytes",
            url, response.status_code, len(response.content)
        )
        return response.text

    # ------------------------------------------------------------------
    # HTML parsing
    # ------------------------------------------------------------------

    def _parse_html(self, html: str, url: str) -> List[EvidenceRecord]:
        """
        Parse HTML and extract motor specification evidence.
        Tries multiple extraction strategies in order.
        """
        soup = BeautifulSoup(html, "lxml")
        evidence = []

        # Remove script/style content
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Strategy 1: HTML tables
        evidence.extend(self._extract_from_tables(soup, url))

        # Strategy 2: Definition lists (dl/dt/dd)
        evidence.extend(self._extract_from_dl(soup, url))

        # Strategy 3: Free text regex
        evidence.extend(self._extract_from_text(soup, url))

        return evidence

    def _get_section_heading(self, element) -> Optional[str]:
        """Find nearest preceding heading for section context."""
        for sibling in element.find_all_previous(["h1", "h2", "h3", "h4"]):
            text = sibling.get_text(strip=True)
            if text:
                return text[:100]
        return None

    def _extract_from_tables(self, soup: BeautifulSoup, url: str) -> List[EvidenceRecord]:
        """Extract motor specs from HTML <table> elements."""
        records = []
        for table in soup.find_all("table"):
            section = self._get_section_heading(table)
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue

            # Try to find header row
            headers = []
            header_row = table.find("thead")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
            elif rows:
                headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
                rows = rows[1:]

            for row in rows:
                cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                if not cells or all(c == "" for c in cells):
                    continue
                row_text = " | ".join(f"{h}: {c}" for h, c in zip(headers, cells) if c)

                for i, (header, cell) in enumerate(zip(headers, cells)):
                    if not cell:
                        continue
                    # Check if header indicates a spec field
                    for pattern, attribute, unit in SPEC_PATTERNS:
                        if re.search(pattern, cell, re.IGNORECASE):
                            match = re.search(pattern, cell, re.IGNORECASE)
                            raw_value = match.group(1) if match else cell
                            try:
                                numeric_value = float(raw_value.replace(",", "."))
                            except (ValueError, AttributeError):
                                numeric_value = None

                            records.append(EvidenceRecord(
                                source_id=self.source_id,
                                source_type="web",
                                product_id=self.product_id,
                                url=url,
                                section=section,
                                attribute=attribute,
                                raw_value=raw_value,
                                value=numeric_value,
                                unit=unit,
                                evidence_text=row_text[:300],
                                method=ExtractionMethod.HTML_TABLE.value,
                                confidence=0.70,
                            ))
                            break   # one match per cell

        return records

    def _extract_from_dl(self, soup: BeautifulSoup, url: str) -> List[EvidenceRecord]:
        """Extract motor specs from HTML <dl>/<dt>/<dd> definition lists."""
        records = []
        for dl in soup.find_all("dl"):
            section = self._get_section_heading(dl)
            terms = dl.find_all("dt")
            defs = dl.find_all("dd")
            for dt, dd in zip(terms, defs):
                label = dt.get_text(strip=True)
                value_text = dd.get_text(strip=True)
                if not value_text:
                    continue
                for pattern, attribute, unit in SPEC_PATTERNS:
                    match = re.search(pattern, value_text, re.IGNORECASE)
                    if match:
                        raw_value = match.group(1)
                        try:
                            numeric_value = float(raw_value.replace(",", "."))
                        except ValueError:
                            numeric_value = None
                        records.append(EvidenceRecord(
                            source_id=self.source_id,
                            source_type="web",
                            product_id=self.product_id,
                            url=url,
                            section=section,
                            attribute=attribute,
                            raw_value=raw_value,
                            value=numeric_value,
                            unit=unit,
                            evidence_text=f"{label}: {value_text}"[:300],
                            method=ExtractionMethod.HTML_DL.value,
                            confidence=0.65,
                        ))
                        break
        return records

    def _extract_from_text(self, soup: BeautifulSoup, url: str) -> List[EvidenceRecord]:
        """Extract motor specs from page free text using regex."""
        records = []
        # Use main content area if identifiable
        main = soup.find(["main", "article"]) or soup.find("body") or soup
        text = main.get_text(separator=" ", strip=True)
        if not text:
            return records

        for pattern, attribute, unit in SPEC_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                raw_value = match.group(1)
                start = max(0, match.start() - 60)
                end = min(len(text), match.end() + 60)
                context = text[start:end].strip()
                try:
                    numeric_value = float(raw_value.replace(",", "."))
                except ValueError:
                    numeric_value = None

                records.append(EvidenceRecord(
                    source_id=self.source_id,
                    source_type="web",
                    product_id=self.product_id,
                    url=url,
                    section=None,
                    attribute=attribute,
                    raw_value=raw_value,
                    value=numeric_value,
                    unit=unit,
                    evidence_text=context[:300],
                    method=ExtractionMethod.HTML_TEXT.value,
                    confidence=0.55,
                ))

        return records


def extract_web_source(
    url_file: Path,
    source_id: str,
    product_id: str,
) -> ExtractionResult:
    """Convenience function: create extractor and extract one web source."""
    extractor = WebExtractor(url_file=url_file, source_id=source_id, product_id=product_id)
    return extractor.extract()


def check_network_available() -> bool:
    """Check if network is available (for test skip decisions)."""
    return _is_network_available()
