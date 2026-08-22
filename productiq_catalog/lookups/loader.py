"""
ProductIQ Catalog Lookup Services & Global Normalization
=========================================================
Loads and caches queryable lookup tables for manufacturers/brands,
UOM standards, and the 63-entry decimal-fraction table.
Provides global placeholder filtering and fuzzy canonicalization.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PLACEHOLDER_STRINGS = {
    "-- unbranded --",
    "-- no unilog brand --",
    "-- no dib brand --",
    "-",
    "commodity - unbranded",
    "none",
    "null",
    "n/a",
    "na",
    "",
}


def is_placeholder(value: Optional[str]) -> bool:
    """
    Check if a string represents a documented placeholder or missing value.
    """
    if value is None:
        return True
    cleaned = value.strip().lower()
    if cleaned.startswith("--") and cleaned.endswith("--"):
        return True
    return cleaned in PLACEHOLDER_STRINGS


def clean_string(value: Optional[str]) -> Optional[str]:
    """
    Return sanitized string or None if the value is a placeholder.
    """
    if is_placeholder(value):
        return None
    return value.strip() if value else None


class DecimalFractionLookup:
    """
    Lookup and converter for the 63 standard fractional inch entries
    and compound dimension strings (e.g. 1-1/2", 7-1/4", 5"x.045"x7/8").
    """

    def __init__(self, json_path: Optional[Path | str] = None):
        self.path = (
            Path(json_path)
            if json_path
            else Path(__file__).resolve().parent.parent.parent
            / "data"
            / "catalog"
            / "lookups"
            / "decimal_fractions.json"
        )
        self._fraction_to_dec: Dict[str, float] = {}
        self._entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._entries = data.get("entries", [])
            for e in self._entries:
                self._fraction_to_dec[e["fraction"]] = e["decimal"]

    def get_all_entries(self) -> List[Dict[str, Any]]:
        return self._entries

    def parse_fraction(self, text: str) -> Optional[float]:
        """
        Convert simple or compound fraction string to float.
        Examples:
          '1/2' -> 0.5
          '7/64' -> 0.109375
          '1-1/2' -> 1.5
          '7 1/4' -> 7.25
        """
        if not text:
            return None
        cleaned = text.strip().replace('"', "").replace("'", "")

        # Check exact match
        if cleaned in self._fraction_to_dec:
            return self._fraction_to_dec[cleaned]

        # Check compound fraction: '1-1/2' or '1 1/2' or '7-1/4'
        match = re.match(r"^(\d+)[\s\-]+(\d+)/(\d+)$", cleaned)
        if match:
            whole = float(match.group(1))
            num = float(match.group(2))
            den = float(match.group(3))
            if den != 0:
                frac = num / den
                return round(whole + frac, 6)

        # Check pure fraction: '3/8'
        match_simple = re.match(r"^(\d+)/(\d+)$", cleaned)
        if match_simple:
            num = float(match_simple.group(1))
            den = float(match_simple.group(2))
            if den != 0:
                return round(num / den, 6)

        # Check direct float: '0.045' or '12'
        try:
            return float(cleaned)
        except ValueError:
            return None


class UOMLookup:
    """
    Standardizes and normalizes Units of Measure against canonical abbreviations
    derived strictly from the Ground Truth delivery format.
    """

    def __init__(self, json_path: Optional[Path | str] = None):
        self.path = (
            Path(json_path)
            if json_path
            else Path(__file__).resolve().parent.parent.parent
            / "data"
            / "catalog"
            / "lookups"
            / "uom_standards.json"
        )
        self._canonical_units: List[str] = []
        self._alias_to_canonical: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._canonical_units = data.get("canonical_units", [])
            for u in self._canonical_units:
                self._alias_to_canonical[u.lower()] = u
            for alias, canon in data.get("observable_alias_mappings", {}).items():
                self._alias_to_canonical[alias.lower()] = canon

    def get_canonical_units(self) -> List[str]:
        return self._canonical_units

    def normalize(self, raw_uom: Optional[str]) -> Optional[str]:
        """
        Map any verified observable alias (e.g. '"', 'in.', 'IN', 'DBA') to canonical ('in', 'dBA').
        Returns None if placeholder or if unverified.
        """
        if not raw_uom or is_placeholder(raw_uom):
            return None
        cleaned = raw_uom.strip()
        return self._alias_to_canonical.get(cleaned.lower(), None)



class ManufacturerBrandLookup:
    """
    Canonicalizes messy raw supplier and brand strings using approved master dictionary.
    Detects brand conflicts across input columns.
    """

    def __init__(self, json_path: Optional[Path | str] = None):
        self.path = (
            Path(json_path)
            if json_path
            else Path(__file__).resolve().parent.parent.parent
            / "data"
            / "catalog"
            / "lookups"
            / "manufacturers_brands.json"
        )
        self._mappings: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._mappings = data.get("mappings", [])

    def get_all_mappings(self) -> List[Dict[str, Any]]:
        return self._mappings

    def match_signal(self, text: Optional[str]) -> Optional[Dict[str, str]]:
        """
        Search master dictionary for matching manufacturer and brand.
        """
        clean_text = clean_string(text)
        if not clean_text:
            return None

        text_lower = clean_text.lower()

        for m in self._mappings:
            for sig in m["raw_signals"]:
                sig_lower = sig.lower()
                if sig_lower == text_lower or (len(sig_lower) >= 3 and sig_lower in text_lower):
                    return {
                        "manufacturer": m["canonical_manufacturer"],
                        "brand": m["canonical_brand"],
                        "trade_name": m.get("trade_name", ""),
                        "matched_signal": sig,
                    }
        return None

    def resolve(
        self,
        part_manuf: Optional[str] = None,
        e1_brand: Optional[str] = None,
        unilog_brand: Optional[str] = None,
        dib_brand: Optional[str] = None,
        part_desc: Optional[str] = None,
        mfg_part_num: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resolve manufacturer, brand, and detect cross-source conflicts.
        """
        c_manuf = clean_string(part_manuf)
        c_e1 = clean_string(e1_brand)
        c_unilog = clean_string(unilog_brand)
        c_dib = clean_string(dib_brand)
        c_desc = clean_string(part_desc)
        c_part_num = clean_string(mfg_part_num)

        # Collect candidate brand signals
        candidates = []
        for src_name, val in [
            ("Mfg_Part_Num", c_part_num),
            ("Part_Manuf", c_manuf),
            ("E1_Brand", c_e1),
            ("DIB_Brand", c_dib),
            ("Unilog_Brand", c_unilog),
            ("Part_Desc", c_desc),
        ]:
            if val:
                matched = self.match_signal(val)
                if matched:
                    candidates.append({"source": src_name, "raw_val": val, **matched})

        if not candidates:
            return {
                "manufacturer": None,
                "brand": None,
                "trade_name": None,
                "status": "Unknown",
                "confidence": 0.0,
                "sources": [],
                "reason": "No manufacturer or brand signal found in input row.",
                "is_conflicted": False,
            }

        # Check for conflicts between distinct non-placeholder brand names
        distinct_brands = {c["brand"] for c in candidates if c.get("brand")}
        distinct_manufs = {c["manufacturer"] for c in candidates if c.get("manufacturer")}

        if len(distinct_brands) > 1:
            sources_list = [f"{c['source']}='{c['raw_val']}'->{c['brand']}" for c in candidates]
            return {
                "manufacturer": list(distinct_manufs)[0] if distinct_manufs else None,
                "brand": None,  # No silent winner picked on conflict
                "trade_name": None,
                "status": "Conflicted",
                "confidence": 0.40,
                "sources": sources_list,
                "reason": f"Conflict: Multiple conflicting brand assertions detected: {', '.join(distinct_brands)}",
                "is_conflicted": True,
            }

        # Primary winner
        best = candidates[0]
        is_exact = any(c["source"] in ["Part_Manuf", "DIB_Brand", "E1_Brand", "Mfg_Part_Num"] for c in candidates)
        status = "Verified" if is_exact else "Inferred"
        conf = 1.0 if is_exact else 0.85
        sources = [f"{c['source']}='{c['raw_val']}'" for c in candidates]

        return {
            "manufacturer": best["manufacturer"],
            "brand": best["brand"],
            "trade_name": best.get("trade_name"),
            "status": status,
            "confidence": conf,
            "sources": sources,
            "reason": f"Canonicalized from approved master table matching '{best['matched_signal']}'.",
            "is_conflicted": False,
        }
