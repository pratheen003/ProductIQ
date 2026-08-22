"""
ProductIQ Catalog Manufacturer & Brand Enricher
================================================
Performs deterministic canonicalization, fuzzy matching, and cross-source conflict
detection for catalog items using the ground-truth verified master dictionary.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from productiq_catalog.schema.models import CatalogField, CatalogTrustStatus, CatalogInputRow
from productiq_catalog.lookups.loader import (
    is_placeholder,
    clean_string,
    ManufacturerBrandLookup,
)


class ManufacturerEnricher:
    """
    Enriches manufacturer, brand, and trade name fields.
    Detects cross-column brand disagreements across input sources.
    """

    def __init__(self, lookup: Optional[ManufacturerBrandLookup] = None):
        self.lookup = lookup or ManufacturerBrandLookup()

    def enrich(self, row: CatalogInputRow) -> Dict[str, CatalogField[str]]:
        """
        Enrich manufacturer_name, brand_name, trade_name from a CatalogInputRow.
        """
        # Step 1: Detect cross-column input signals
        c_manuf = clean_string(row.part_manuf)
        c_e1 = clean_string(row.e1_brand)
        c_unilog = clean_string(row.unilog_brand)
        c_dib = clean_string(row.dib_brand)
        c_desc = clean_string(row.part_desc)
        c_part = clean_string(row.mfg_part_num)

        # Step 2: Check for direct brand conflict among non-placeholder input columns
        # (e.g. E1_Brand="TREX" vs DIB_Brand="Milwaukee" vs Part_Manuf="Freud Inc")
        raw_brands = {}
        if c_e1:
            raw_brands["E1_Brand"] = c_e1
        if c_unilog:
            raw_brands["Unilog_Brand"] = c_unilog
        if c_dib:
            raw_brands["DIB_Brand"] = c_dib

        # Extract brand token from part_manuf (e.g. "Freud Inc" from "Freud Inc (2435)")
        manuf_brand_token = None
        if c_manuf:
            # Strip trailing supplier code like '(2435)'
            clean_m = re.sub(r"\s*\([^\)]*\)\s*$", "", c_manuf).strip()
            if clean_m:
                manuf_brand_token = clean_m

        # Collect distinct brand identity signals
        distinct_raw_brands = set(raw_brands.values())
        if manuf_brand_token and manuf_brand_token not in distinct_raw_brands:
            # If part_manuf is something like "Appliance Dealers Cooperative", it's a distributor
            # Only consider it conflicting if it's a distinct manufacturing brand
            if not any(dist in manuf_brand_token.lower() for dist in ["cooperative", "supply", "distributor", "lumber"]):
                distinct_raw_brands.add(manuf_brand_token)

        # Step 3: Query verified lookup dictionary
        resolution = self.lookup.resolve(
            part_manuf=row.part_manuf,
            e1_brand=row.e1_brand,
            unilog_brand=row.unilog_brand,
            dib_brand=row.dib_brand,
            part_desc=row.part_desc,
            mfg_part_num=row.mfg_part_num,
        )

        # Check if there is an explicit cross-column conflict
        is_conflicted = len(distinct_raw_brands) > 1 or resolution.get("is_conflicted", False)

        if is_conflicted and not resolution.get("manufacturer"):
            # Conflicted input signals with no single verified ground-truth resolution
            sources_list = [f"{k}='{v}'" for k, v in raw_brands.items()]
            if c_manuf:
                sources_list.append(f"Part_Manuf='{c_manuf}'")

            reason_str = (
                f"Conflicted: Incompatible brand assertions detected across input columns: "
                f"{', '.join(distinct_raw_brands)}. No arbitrary winner picked."
            )
            return {
                "manufacturer_name": CatalogField[str](
                    value=None,
                    status=CatalogTrustStatus.CONFLICTED,
                    confidence=0.40,
                    sources=sources_list,
                    reason=reason_str,
                ),
                "brand_name": CatalogField[str](
                    value=None,
                    status=CatalogTrustStatus.CONFLICTED,
                    confidence=0.40,
                    sources=sources_list,
                    reason=reason_str,
                ),
                "trade_name": CatalogField[str](
                    value=None,
                    status=CatalogTrustStatus.UNKNOWN,
                    confidence=0.0,
                    sources=[],
                    reason="Trade name undetermined due to brand conflict.",
                ),
            }

        # If matched in verified ground truth
        if resolution.get("manufacturer") and resolution.get("brand"):
            manuf_val = resolution["manufacturer"]
            brand_val = resolution["brand"]
            trade_val = resolution.get("trade_name") or ""
            status_enum = (
                CatalogTrustStatus.VERIFIED
                if resolution["status"] == "Verified"
                else CatalogTrustStatus.INFERRED
            )

            return {
                "manufacturer_name": CatalogField[str](
                    value=manuf_val,
                    status=status_enum,
                    confidence=resolution["confidence"],
                    sources=resolution["sources"],
                    reason=resolution["reason"],
                ),
                "brand_name": CatalogField[str](
                    value=brand_val,
                    status=status_enum,
                    confidence=resolution["confidence"],
                    sources=resolution["sources"],
                    reason=resolution["reason"],
                ),
                "trade_name": CatalogField[str](
                    value=trade_val if trade_val else None,
                    status=CatalogTrustStatus.VERIFIED if trade_val else CatalogTrustStatus.UNKNOWN,
                    confidence=1.0 if trade_val else 0.0,
                    sources=resolution["sources"] if trade_val else [],
                    reason="Verified from ground truth reference." if trade_val else "Not specified in ground truth.",
                ),
            }

        # Otherwise: unverified entry outside ground truth coverage -> Unknown (No Fabrication)
        sources_list = []
        if c_manuf:
            sources_list.append(f"Part_Manuf='{c_manuf}'")
        if c_e1:
            sources_list.append(f"E1_Brand='{c_e1}'")
        if c_dib:
            sources_list.append(f"DIB_Brand='{c_dib}'")
        if c_part:
            sources_list.append(f"Mfg_Part_Num='{c_part}'")

        reason_str = (
            "Unknown: Supplier/brand not present in verified master lookup table. "
            "Value suppressed to prevent data fabrication."
        )

        return {
            "manufacturer_name": CatalogField[str](
                value=None,
                status=CatalogTrustStatus.UNKNOWN,
                confidence=0.0,
                sources=sources_list,
                reason=reason_str,
            ),
            "brand_name": CatalogField[str](
                value=None,
                status=CatalogTrustStatus.UNKNOWN,
                confidence=0.0,
                sources=sources_list,
                reason=reason_str,
            ),
            "trade_name": CatalogField[str](
                value=None,
                status=CatalogTrustStatus.UNKNOWN,
                confidence=0.0,
                sources=[],
                reason="Unknown: No verified trade name available.",
            ),
        }
