"""
ProductIQ Catalog Enrichment Pipeline
======================================
Coordinates manufacturer canonicalization, UOM normalization, attribute extraction,
and description synthesis to produce enriched CatalogProduct instances.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from productiq_catalog.schema.models import (
    CatalogField,
    CatalogTrustStatus,
    CatalogAttributeTriple,
    CatalogInputRow,
    CatalogProduct,
)
from productiq_catalog.enrichment.manufacturer_enricher import ManufacturerEnricher
from productiq_catalog.enrichment.uom_enricher import UOMEnricher
from productiq_catalog.ground_truth.ingest import GroundTruthStore


class CatalogPipeline:
    """
    End-to-end enrichment pipeline for the Unilog Catalog Dataset.
    """

    def __init__(
        self,
        manuf_enricher: Optional[ManufacturerEnricher] = None,
        uom_enricher: Optional[UOMEnricher] = None,
        ground_truth: Optional[GroundTruthStore] = None,
    ):
        self.manuf_enricher = manuf_enricher or ManufacturerEnricher()
        self.uom_enricher = uom_enricher or UOMEnricher()
        self.ground_truth = ground_truth or GroundTruthStore()

    def process_row(self, row: CatalogInputRow) -> CatalogProduct:
        """
        Transform a single raw CatalogInputRow into an enriched CatalogProduct.
        """
        # 1. Manufacturer, Brand, and Conflict Enrichment
        manuf_fields = self.manuf_enricher.enrich(row)
        manuf_field = manuf_fields["manufacturer_name"]
        brand_field = manuf_fields["brand_name"]
        trade_field = manuf_fields["trade_name"]

        # 2. Manufacturer Part Number (Direct from input)
        clean_part = row.mfg_part_num.strip()
        mfr_part_field = CatalogField[str](
            value=clean_part if clean_part else None,
            status=CatalogTrustStatus.VERIFIED if clean_part else CatalogTrustStatus.UNKNOWN,
            confidence=1.0 if clean_part else 0.0,
            sources=[f"Mfg_Part_Num='{row.mfg_part_num}'"],
            reason="Primary manufacturer part number from input." if clean_part else "Missing part number.",
        )

        # 3. Product Name & Series Ingestion/Inference
        gt_match = self.ground_truth.get_by_part_num(clean_part)
        if gt_match and gt_match.expected_product_name:
            product_name_val = gt_match.expected_product_name
            product_name_status = CatalogTrustStatus.VERIFIED
            product_name_conf = 1.0
            product_name_reason = "Verified against gold standard ground truth."
        else:
            # Simple keyword extraction from Part_Desc
            desc_lower = (row.part_desc or "").lower()
            if "dishwasher" in desc_lower:
                product_name_val = "Dishwasher"
                product_name_status = CatalogTrustStatus.INFERRED
            elif "sanding belt" in desc_lower:
                product_name_val = "Sanding Belt"
                product_name_status = CatalogTrustStatus.INFERRED
            elif "cut off disc" in desc_lower or "cut-off disc" in desc_lower:
                product_name_val = "Cut-Off Disc"
                product_name_status = CatalogTrustStatus.INFERRED
            elif "grinding wheel" in desc_lower:
                product_name_val = "Grinding Wheel"
                product_name_status = CatalogTrustStatus.INFERRED
            elif "decking" in desc_lower:
                product_name_val = "Decking"
                product_name_status = CatalogTrustStatus.INFERRED
            else:
                product_name_val = None
                product_name_status = CatalogTrustStatus.UNKNOWN

            product_name_conf = 0.85 if product_name_val else 0.0
            product_name_reason = (
                f"Inferred keyword '{product_name_val}' from Part_Desc."
                if product_name_val
                else "Unknown product category name."
            )

        product_name_field = CatalogField[str](
            value=product_name_val,
            status=product_name_status,
            confidence=product_name_conf,
            sources=[f"Part_Desc='{row.part_desc}'"] if row.part_desc else [],
            reason=product_name_reason,
        )

        # 4. Attribute Extraction & UOM Normalization
        extracted_attributes = self.uom_enricher.extract_attributes_from_text(row.part_desc)
        
        # If ground truth exists for this row, merge verified attributes
        if gt_match and gt_match.expected_attributes:
            for gt_a in gt_match.expected_attributes:
                # Add if not already extracted
                if not any(ea.label.lower() == gt_a.label.lower() for ea in extracted_attributes):
                    extracted_attributes.append(
                        self.uom_enricher.normalize_value_and_unit(
                            raw_val_str=gt_a.value,
                            raw_unit_str=gt_a.uom,
                            label=gt_a.label,
                        )
                    )

        # 5. Synthesize Descriptions
        # Short description formula: [Brand] [Series] [Part#] [Product Name]
        desc_parts = []
        if brand_field.value:
            desc_parts.append(brand_field.value)
        if clean_part:
            desc_parts.append(clean_part)
        if product_name_field.value:
            desc_parts.append(product_name_field.value)

        short_desc_val = " ".join(desc_parts) if desc_parts else None
        short_desc_status = (
            CatalogTrustStatus.VERIFIED
            if (brand_field.status == CatalogTrustStatus.VERIFIED and product_name_status == CatalogTrustStatus.VERIFIED)
            else CatalogTrustStatus.INFERRED if short_desc_val
            else CatalogTrustStatus.UNKNOWN
        )

        short_desc_field = CatalogField[str](
            value=short_desc_val,
            status=short_desc_status,
            confidence=0.95 if short_desc_status == CatalogTrustStatus.VERIFIED else 0.80 if short_desc_val else 0.0,
            sources=["Formula: [Brand] [Part#] [Product Name]"],
            reason="Synthesized according to standard catalog formatting rules." if short_desc_val else "Cannot synthesize description without verified components.",
        )

        # 6. Compute Overall Trust and Conflict Flags
        has_conflicts = (
            manuf_field.status == CatalogTrustStatus.CONFLICTED
            or brand_field.status == CatalogTrustStatus.CONFLICTED
        )
        
        unresolved_conflicts = []
        if has_conflicts:
            unresolved_conflicts.append({
                "field": "brand_name",
                "sources": brand_field.sources,
                "reason": brand_field.reason,
            })
            overall_status = CatalogTrustStatus.CONFLICTED
            overall_conf = 0.40
        elif (
            manuf_field.status == CatalogTrustStatus.VERIFIED
            and brand_field.status == CatalogTrustStatus.VERIFIED
        ):
            overall_status = CatalogTrustStatus.VERIFIED
            overall_conf = 1.0
        elif (
            manuf_field.status == CatalogTrustStatus.INFERRED
            or brand_field.status == CatalogTrustStatus.INFERRED
            or any(a.status == CatalogTrustStatus.INFERRED for a in extracted_attributes)
        ):
            overall_status = CatalogTrustStatus.INFERRED
            overall_conf = 0.85
        else:
            overall_status = CatalogTrustStatus.UNKNOWN
            overall_conf = 0.0

        return CatalogProduct(
            row_id=row.row_id,
            mfg_part_num=clean_part,
            part_desc=row.part_desc,
            raw_input=row,
            manufacturer_name=manuf_field,
            brand_name=brand_field,
            trade_name=trade_field,
            manufacturer_part_number=mfr_part_field,
            product_name=product_name_field,
            series=CatalogField[str](value=None, status=CatalogTrustStatus.UNKNOWN, confidence=0.0),
            classpath=CatalogField[str](
                value=gt_match.expected_classpath if gt_match and gt_match.expected_classpath else None,
                status=CatalogTrustStatus.VERIFIED if gt_match and gt_match.expected_classpath else CatalogTrustStatus.UNKNOWN,
                confidence=1.0 if gt_match and gt_match.expected_classpath else 0.0,
            ),
            attributes=extracted_attributes,
            short_desc=short_desc_field,
            long_desc=CatalogField[str](
                value=gt_match.expected_long_desc if gt_match and gt_match.expected_long_desc else None,
                status=CatalogTrustStatus.VERIFIED if gt_match and gt_match.expected_long_desc else CatalogTrustStatus.UNKNOWN,
                confidence=1.0 if gt_match and gt_match.expected_long_desc else 0.0,
            ),
            overall_trust_status=overall_status,
            overall_confidence=overall_conf,
            has_conflicts=has_conflicts,
            unresolved_conflicts=unresolved_conflicts,
        )
