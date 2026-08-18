"""
ProductIQ PDF Extractor — WEG Brochure
========================================
Extracts raw motor specification evidence from the WEG W22 Severe Process IE3 brochure.

The WEG brochure uses a fixed-position column layout across pages 5–7.
Column mapping (0-indexed) based on observed PDF structure:
  0  = rated_power (kW)
  1  = rated_power_hp (HP)  — kept as raw, not a canonical field
  2  = frame_size
  3  = torque_full_load_nm  — not in canonical schema, preserved as raw
  4  = locked_rotor_current_ratio  — raw, not canonical
  5  = locked_rotor_torque_ratio   — raw, not canonical
  6  = breakdown_torque_ratio      — raw, not canonical
  7  = inertia_kgm2               — raw, not canonical
  8  = locked_rotor_time_hot_s     — raw, not canonical
  9  = locked_rotor_time_cold_s    — raw, not canonical
  10 = weight (kg)
  11 = sound_dba                   — raw, not canonical
  12 = rated_speed (rpm)
  13 = efficiency_at_50pct        — raw (phase 2 picks 100%)
  14 = efficiency_at_75pct        — raw
  15 = efficiency (%) [at 100% load — canonical]
  16 = power_factor_at_50pct      — raw
  17 = power_factor_at_75pct      — raw
  18 = power_factor               — dimensionless [at 100% load — canonical]
  19 = rated_current (A)

Section headings on each page identify the pole configuration.
Rated voltage (400 V) and frequency (50 Hz) are table-level constants in text.

Provenance per EvidenceRecord:
  source_id, source_type="pdf", product_id, page, section, attribute,
  raw_value, value, unit, evidence_text (row context), method, confidence.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber

from productiq.extraction.models import (
    EvidenceRecord,
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
)

logger = logging.getLogger("productiq.extraction.pdf")

# ---------------------------------------------------------------------------
# Fixed column position → (attribute_name, unit, canonical)
# canonical=True means this maps to a ProductIQ MotorProduct field
# ---------------------------------------------------------------------------
COLUMN_MAP: Dict[int, Tuple[str, Optional[str], bool]] = {
    0:  ("rated_power",                  "kW",   True),
    1:  ("rated_power_hp",               "HP",   False),   # raw, not canonical
    2:  ("frame_size",                   None,   True),
    3:  ("full_load_torque_nm",          "Nm",   False),
    4:  ("locked_rotor_current_ratio",   None,   False),
    5:  ("locked_rotor_torque_ratio",    None,   False),
    6:  ("breakdown_torque_ratio",       None,   False),
    7:  ("inertia_kgm2",                 "kgm2", False),
    8:  ("locked_rotor_time_hot_s",      "s",    False),
    9:  ("locked_rotor_time_cold_s",     "s",    False),
    10: ("weight",                       "kg",   True),
    11: ("sound_dba",                    "dB(A)", False),
    12: ("rated_speed",                  "rpm",  True),
    13: ("efficiency_at_50pct_load",     "%",    False),
    14: ("efficiency_at_75pct_load",     "%",    False),
    15: ("efficiency",                   "%",    True),    # at 100% load
    16: ("power_factor_at_50pct_load",   None,   False),
    17: ("power_factor_at_75pct_load",   None,   False),
    18: ("power_factor",                 None,   True),   # at 100% load
    19: ("rated_current",                "A",    True),
}

# Data pages: which pages to scan for electrical data tables
DATA_PAGES = {5, 6, 7}   # 4-pole(p5), 6-pole(p6), 8-pole(p7) in this brochure
# Table-level constants extracted from page text
GLOBAL_CONSTANTS = {
    "rated_voltage": ("400", "V"),
    "frequency":     ("50",  "Hz"),
}


def _parse_numeric(raw: str) -> Optional[float]:
    if not raw or not raw.strip():
        return None
    raw = raw.strip().replace(",", ".")
    m = re.search(r"[-+]?\d+\.?\d*", raw)
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def _detect_poles_from_text(text: str) -> Optional[int]:
    """Extract pole count from page text. E.g. 'II pole'→2, 'IV pole'→4, 'VI pole'→6."""
    roman = {"II": 2, "IV": 4, "VI": 6, "VIII": 8}
    for roman_str, val in roman.items():
        if re.search(rf"\b{roman_str}\s*(pole|pol)", text, re.IGNORECASE):
            return val
    m = re.search(r"(\d+)\s*pole", text, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def _match_product(
    power_kw: float,
    poles: Optional[int],
    manifest_products: Dict[str, dict],
) -> Optional[str]:
    """
    Find the product_id in the manifest that matches (power_kw, poles).
    Returns None if no match.
    """
    for pid in manifest_products:
        parts = pid.split("-")
        if len(parts) < 4:
            continue
        try:
            pid_power = float(parts[-1])
            pid_pole_str = parts[-2]  # e.g. "4P"
            pid_poles = int(pid_pole_str.replace("P", ""))
        except (ValueError, IndexError):
            continue
        if abs(power_kw - pid_power) < 0.05 and (poles is None or poles == pid_poles):
            return pid
    return None


class PDFExtractor:
    """
    Extracts raw motor specification evidence from the WEG W22 Severe Process brochure.
    Uses positional column mapping (not header detection) based on the real PDF structure.
    """

    def __init__(
        self,
        pdf_path: Path,
        source_id: str,
        manifest_products: Dict[str, dict],
    ):
        self.pdf_path = pdf_path
        self.source_id = source_id
        self.manifest_products = manifest_products

    def extract_all(self) -> List[ExtractionResult]:
        if not self.pdf_path.exists():
            return [ExtractionResult.failure(
                source_id=self.source_id,
                source_type="pdf",
                product_id="UNKNOWN",
                error=f"PDF file not found: {self.pdf_path}",
                source_ref=str(self.pdf_path),
            )]
        try:
            return self._process_pdf()
        except Exception as exc:
            logger.error("PDF extraction failed: %s", exc, exc_info=True)
            return [ExtractionResult.failure(
                source_id=self.source_id,
                source_type="pdf",
                product_id="UNKNOWN",
                error=f"PDF error: {exc}",
                source_ref=str(self.pdf_path),
            )]

    def _process_pdf(self) -> List[ExtractionResult]:
        # product_id → list of EvidenceRecord
        evidence_by_product: Dict[str, List[EvidenceRecord]] = {}
        pages_read = 0

        with pdfplumber.open(self.pdf_path) as pdf:
            total = len(pdf.pages)
            logger.info(
                "PDF opened: %s | pages=%d | source_id=%s",
                self.pdf_path.name, total, self.source_id
            )

            for page_obj in pdf.pages:
                pn = page_obj.page_number
                pages_read += 1

                try:
                    text = page_obj.extract_text() or ""
                    poles = _detect_poles_from_text(text)

                    # Extract global constants from all pages
                    if "400" in text and "V" in text:
                        global_records = self._extract_global_constants(
                            text=text, page=pn, poles=poles
                        )
                        for r in global_records:
                            evidence_by_product.setdefault(r.product_id, []).append(r)

                    # Only extract electrical data from known data pages
                    if pn not in DATA_PAGES:
                        continue

                    tables = page_obj.extract_tables()
                    for t_idx, table in enumerate(tables):
                        if not table:
                            continue
                        records = self._process_data_table(
                            table=table,
                            page=pn,
                            poles=poles,
                            t_idx=t_idx,
                        )
                        for r in records:
                            evidence_by_product.setdefault(r.product_id, []).append(r)

                except Exception as page_exc:
                    logger.warning("PDF p.%d error: %s", pn, page_exc)
                    continue

        # Build results
        results = []
        for product_id, evidence in evidence_by_product.items():
            results.append(ExtractionResult(
                source_id=self.source_id,
                source_type="pdf",
                product_id=product_id,
                status=ExtractionStatus.SUCCESS.value,
                evidence=evidence,
                source_ref=str(self.pdf_path),
                pages_read=pages_read,
            ))
            logger.info("PDF: product=%s | evidence=%d", product_id, len(evidence))

        if not results:
            return [ExtractionResult(
                source_id=self.source_id,
                source_type="pdf",
                product_id="UNKNOWN",
                status=ExtractionStatus.PARTIAL.value,
                evidence=[],
                error="No product rows matched manifest products",
                source_ref=str(self.pdf_path),
                pages_read=pages_read,
            )]

        return results

    def _process_data_table(
        self,
        table: List[List],
        page: int,
        poles: Optional[int],
        t_idx: int,
    ) -> List[EvidenceRecord]:
        """
        Process a positional data table (not header-based).
        TABLE 0 is typically a multi-row header block (skip).
        TABLE 1 is the data block.
        """
        records = []

        # Determine if this is a data table: first cell should be parseable as kW
        for row in table:
            if not row:
                continue
            first = str(row[0]).strip() if row[0] else ""
            power_val = _parse_numeric(first)
            if power_val is None or power_val > 1000:
                continue   # not a data row

            cells = [str(c).strip() if c is not None else "" for c in row]
            row_text = " | ".join(
                f"col{i}={v}" for i, v in enumerate(cells) if v
            )

            # Match to a product
            product_id = _match_product(power_val, poles, self.manifest_products)
            if not product_id:
                # Record with UNKNOWN id — may be a pole configuration not in manifest
                product_id = f"PDF-P{page}-kW{first}"

            # Section string
            pole_str = f"{poles}-pole" if poles else "unknown-pole"
            section = f"p.{page}, {pole_str} electrical data table"

            # Extract each column
            for col_idx, (attribute, unit, _canonical) in COLUMN_MAP.items():
                if col_idx >= len(cells):
                    break
                raw_value = cells[col_idx]
                if not raw_value:
                    continue
                numeric = _parse_numeric(raw_value)

                records.append(EvidenceRecord(
                    source_id=self.source_id,
                    source_type="pdf",
                    product_id=product_id,
                    page=page,
                    section=section,
                    attribute=attribute,
                    raw_value=raw_value,
                    value=numeric,
                    unit=unit,
                    evidence_text=row_text[:300],
                    method=ExtractionMethod.TABLE.value,
                    confidence=0.92,
                ))

        return records

    def _extract_global_constants(
        self,
        text: str,
        page: int,
        poles: Optional[int],
    ) -> List[EvidenceRecord]:
        """
        Extract table-wide constants (400 V, 50 Hz) from page text.
        These apply globally to all products on the page, recorded as GLOBAL.
        """
        records = []
        for attribute, (value_str, unit) in GLOBAL_CONSTANTS.items():
            pattern = rf"\b{re.escape(value_str)}\s*{re.escape(unit)}\b"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                context = text[start:end].replace("\n", " ").strip()
                records.append(EvidenceRecord(
                    source_id=self.source_id,
                    source_type="pdf",
                    product_id="GLOBAL",
                    page=page,
                    section=f"p.{page} page-level text",
                    attribute=attribute,
                    raw_value=value_str,
                    value=_parse_numeric(value_str),
                    unit=unit,
                    evidence_text=context[:300],
                    method=ExtractionMethod.TEXT.value,
                    confidence=0.80,
                ))
        return records
