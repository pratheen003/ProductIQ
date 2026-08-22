"""
ProductIQ Catalog UOM & Dimension Normalization Enricher
=========================================================
Extracts physical and electrical specifications from text, standardizes units
against verified canonical forms (V, A, in, dBA), and converts fractional
measurements via the 63-entry decimal fraction table.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from productiq_catalog.schema.models import CatalogAttributeTriple, CatalogTrustStatus
from productiq_catalog.lookups.loader import (
    UOMLookup,
    DecimalFractionLookup,
    clean_string,
)


class UOMEnricher:
    """
    Parses and normalizes dimensional, electrical, and acoustic units.
    """

    def __init__(
        self,
        uom_lookup: Optional[UOMLookup] = None,
        fraction_lookup: Optional[DecimalFractionLookup] = None,
    ):
        self.uom_lookup = uom_lookup or UOMLookup()
        self.fraction_lookup = fraction_lookup or DecimalFractionLookup()

    def normalize_unit(self, raw_uom: Optional[str]) -> Tuple[Optional[str], CatalogTrustStatus]:
        """
        Standardize raw unit against verified canonical forms.
        """
        if not raw_uom:
            return None, CatalogTrustStatus.UNKNOWN

        cleaned = raw_uom.strip()
        canon = self.uom_lookup.normalize(cleaned)

        if canon is None:
            return cleaned, CatalogTrustStatus.UNKNOWN

        # If it was already exactly in canonical form
        if cleaned == canon:
            return canon, CatalogTrustStatus.VERIFIED

        # If it was mapped from an observable alias (e.g. '"', 'IN', 'DBA')
        return canon, CatalogTrustStatus.INFERRED

    def normalize_value_and_unit(
        self,
        raw_val_str: str,
        raw_unit_str: Optional[str] = None,
        label: str = "Dimension",
    ) -> CatalogAttributeTriple:
        """
        Convert numeric/fractional value and normalize its unit.
        """
        clean_val = raw_val_str.strip()
        parsed_numeric = self.fraction_lookup.parse_fraction(clean_val)
        final_val: Any = parsed_numeric if parsed_numeric is not None else clean_val

        canon_uom, uom_status = self.normalize_unit(raw_unit_str)

        # Determine overall status and confidence
        if uom_status == CatalogTrustStatus.VERIFIED and parsed_numeric is not None:
            status = CatalogTrustStatus.VERIFIED
            conf = 1.0
            reason = f"Verified canonical unit '{canon_uom}' with verified numeric value."
        elif uom_status == CatalogTrustStatus.INFERRED or (parsed_numeric is not None and parsed_numeric != clean_val):
            status = CatalogTrustStatus.INFERRED
            conf = 0.90
            reason = f"Normalized from raw '{raw_val_str}{raw_unit_str or ''}' using verified alias/fraction lookup."
        else:
            status = CatalogTrustStatus.UNKNOWN
            conf = 0.50
            reason = f"Unverified unit or format '{raw_unit_str or 'None'}'."

        return CatalogAttributeTriple(
            label=label,
            value=final_val,
            uom=canon_uom,
            raw_value=raw_val_str,
            raw_uom=raw_unit_str,
            status=status,
            confidence=conf,
            reason=reason,
        )

    def extract_attributes_from_text(self, text: Optional[str]) -> List[CatalogAttributeTriple]:
        """
        Extract recognizable physical attributes (Voltage, Current, Sound, Dimensions) from description text.
        """
        results: List[CatalogAttributeTriple] = []
        if not text:
            return results

        # 1. Voltage Rating: e.g. '120V', '120 V', '230V'
        v_matches = re.finditer(r"\b(\d+(?:\.\d+)?)\s*(?:VAC|VDC|V|volts?)\b", text, re.IGNORECASE)
        for m in v_matches:
            results.append(
                self.normalize_value_and_unit(
                    raw_val_str=m.group(1),
                    raw_unit_str="V",
                    label="Voltage Rating",
                )
            )

        # 2. Amperage Rating: e.g. '15A', '10 A', '15 Amps'
        a_matches = re.finditer(r"\b(\d+(?:\.\d+)?)\s*(?:A|amps?|amperes?)\b", text, re.IGNORECASE)
        for m in a_matches:
            results.append(
                self.normalize_value_and_unit(
                    raw_val_str=m.group(1),
                    raw_unit_str="A",
                    label="Amperage Rating",
                )
            )

        # 3. Sound Level: e.g. '41 dBA', '41DBA', '47 dBA'
        dba_matches = re.finditer(r"\b(\d+(?:\.\d+)?)\s*(?:dBA|DBA|db)\b", text, re.IGNORECASE)
        for m in dba_matches:
            results.append(
                self.normalize_value_and_unit(
                    raw_val_str=m.group(1),
                    raw_unit_str="dBA",
                    label="Sound Level",
                )
            )

        # 4. Fractional Dimensions: e.g. '50-1/4IN', '50-1/4 in', '24-1/4 in', '1/2"x18"', '5"x.045"x7/8"'
        dim_matches = re.finditer(
            r"\b((?:\d+[\s\-]*)?\d+/\d+|\d+(?:\.\d+)?)\s*(IN|in\.|\"|in)\b", text, re.IGNORECASE
        )
        for m in dim_matches:
            raw_val = m.group(1).strip()
            raw_uom = m.group(2).strip()
            # Avoid duplicating electrical ratings
            if not raw_val.isdigit() or int(raw_val) < 100:  # e.g. 50-1/4, 24, 18, 5
                results.append(
                    self.normalize_value_and_unit(
                        raw_val_str=raw_val,
                        raw_unit_str=raw_uom,
                        label="Dimension / Size",
                    )
                )

        return results
