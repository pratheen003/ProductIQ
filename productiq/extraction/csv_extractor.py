"""
ProductIQ CSV Extractor
========================
Extracts raw motor specification evidence from legacy-style CSV catalog files.

Target: data/csv/legacy_motors.csv
Strategy: pandas-free CSV reading; column alias mapping; per-row EvidenceRecord.

Provenance per EvidenceRecord:
  source_id, source_type="csv", product_id, row (1-indexed, header excluded),
  column (original column name), attribute (mapped name), raw_value, unit,
  evidence_text (full row context), method="column", confidence.

Rules:
  - Never silently discard unknown columns — preserve them with attribute=column_name.
  - Never convert units (Phase 2).
  - Preserve empty cell as missing (no EvidenceRecord) — do not fabricate values.
  - Provenance note: this CSV is labeled as brochure-derived; that label is carried
    through in source_id and never altered.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional

from productiq.extraction.models import (
    EvidenceRecord,
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
)

logger = logging.getLogger("productiq.extraction.csv")

# ---------------------------------------------------------------------------
# Column alias map — CSV column name → canonical attribute
# Keep explicit. Do not perform semantic normalisation here.
# ---------------------------------------------------------------------------
COLUMN_ALIASES: Dict[str, str] = {
    "product_id":           "product_id",       # identity, not a FieldValue
    "manufacturer":         "manufacturer",
    "model":                "model",
    "rated_power_kw":       "rated_power",
    "rated_power":          "rated_power",
    "rated_power_raw":      "rated_power_raw",  # raw string preserved separately
    "rated_power_unit":     "rated_power_unit", # unit column
    "full_load_current_a":  "rated_current",
    "current_unit":         "rated_current_unit",
    "rated_speed_rpm":      "rated_speed",
    "efficiency_percent":   "efficiency",
    "power_factor":         "power_factor",
    "weight_kg":            "weight",
    "frame":                "frame_size",
    "ip_note":              "ip_rating_note",    # not a clean IP rating; keep as note
    "source_location":      "source_location",  # provenance metadata
}

# Which columns carry extractable numeric/string values for motor specs
SPEC_COLUMNS = {
    "rated_power_kw", "rated_power", "full_load_current_a",
    "rated_speed_rpm", "efficiency_percent", "power_factor",
    "weight_kg", "frame", "ip_note",
}

# Inferred unit for mapped attributes (when no unit column exists)
ATTRIBUTE_UNITS: Dict[str, Optional[str]] = {
    "rated_power":   "kW",
    "rated_current": "A",
    "rated_speed":   "rpm",
    "efficiency":    "%",
    "power_factor":  None,
    "weight":        "kg",
    "frame_size":    None,
    "ip_rating_note": None,
}


def _parse_numeric(raw: str) -> Optional[float]:
    """Parse first numeric from a raw string."""
    import re
    if not raw or raw.strip() == "":
        return None
    m = re.search(r"[-+]?\d+\.?\d*", raw.strip())
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


class CSVExtractor:
    """
    Extracts raw motor specification evidence from a legacy CSV catalog file.

    Usage:
        extractor = CSVExtractor(csv_path, source_id, manifest_products)
        results = extractor.extract_all()  # List[ExtractionResult]
    """

    def __init__(
        self,
        csv_path: Path,
        source_id: str,
        manifest_products: Dict[str, dict],
    ):
        self.csv_path = csv_path
        self.source_id = source_id
        self.manifest_products = manifest_products

    def extract_all(self) -> List[ExtractionResult]:
        """
        Process all rows of the CSV.
        Returns one ExtractionResult per product row.
        Continues past individual row errors.
        """
        if not self.csv_path.exists():
            return [ExtractionResult.failure(
                source_id=self.source_id,
                source_type="csv",
                product_id="UNKNOWN",
                error=f"CSV file not found: {self.csv_path}",
                source_ref=str(self.csv_path),
            )]

        try:
            return self._process_csv()
        except Exception as exc:
            logger.error("CSV extraction failed: %s", exc, exc_info=True)
            return [ExtractionResult.failure(
                source_id=self.source_id,
                source_type="csv",
                product_id="UNKNOWN",
                error=f"CSV open/parse error: {exc}",
                source_ref=str(self.csv_path),
            )]

    def _process_csv(self) -> List[ExtractionResult]:
        results = []
        rows_read = 0

        with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            logger.info(
                "CSV opened: %s | columns=%d | source_id=%s",
                self.csv_path.name, len(headers), self.source_id
            )

            for row_num, row in enumerate(reader, start=1):
                rows_read += 1
                # Skip entirely blank rows
                if all(v is None or v.strip() == "" for v in row.values()):
                    continue

                product_id = row.get("product_id", "").strip()
                if not product_id:
                    logger.warning("CSV row %d: missing product_id, skipping", row_num)
                    continue

                # Validate product_id is in manifest
                if product_id not in self.manifest_products:
                    logger.warning(
                        "CSV row %d: product_id '%s' not in manifest", row_num, product_id
                    )
                    # Still extract — may be useful for debugging

                evidence = self._extract_row(
                    row=row,
                    row_num=row_num,
                    product_id=product_id,
                    headers=headers,
                )

                results.append(ExtractionResult(
                    source_id=self.source_id,
                    source_type="csv",
                    product_id=product_id,
                    status=ExtractionStatus.SUCCESS.value,
                    evidence=evidence,
                    source_ref=str(self.csv_path),
                    rows_read=row_num,
                ))
                logger.debug(
                    "CSV row %d: product=%s | evidence=%d",
                    row_num, product_id, len(evidence)
                )

        if not results:
            return [ExtractionResult.failure(
                source_id=self.source_id,
                source_type="csv",
                product_id="UNKNOWN",
                error="CSV file opened but no data rows found",
                source_ref=str(self.csv_path),
            )]

        logger.info("CSV extraction complete | products=%d | total_rows=%d", len(results), rows_read)
        return results

    def _extract_row(
        self,
        row: Dict[str, str],
        row_num: int,
        product_id: str,
        headers: List[str],
    ) -> List[EvidenceRecord]:
        """Extract all non-empty columns from one CSV row as EvidenceRecords."""
        evidence = []

        # Build a full-row context string for evidence_text
        row_context = "; ".join(
            f"{col}={val}" for col, val in row.items()
            if val and val.strip() and col != "product_id"
        )

        for col_name in headers:
            raw_value = (row.get(col_name) or "").strip()

            # Skip empty cells — do not fabricate
            if not raw_value:
                continue

            # Skip identity columns that are not specs
            if col_name in ("product_id", "manufacturer", "model"):
                continue

            attribute = COLUMN_ALIASES.get(col_name, col_name)
            unit = ATTRIBUTE_UNITS.get(attribute)
            numeric = _parse_numeric(raw_value)

            # Confidence: higher for known-alias columns, lower for unmapped
            confidence = 0.85 if col_name in COLUMN_ALIASES else 0.60

            rec = EvidenceRecord(
                source_id=self.source_id,
                source_type="csv",
                product_id=product_id,
                row=row_num,
                column=col_name,
                attribute=attribute,
                raw_value=raw_value,
                value=numeric,
                unit=unit,
                evidence_text=row_context[:300],
                method=ExtractionMethod.COLUMN.value,
                confidence=confidence,
            )
            evidence.append(rec)

        return evidence
