"""
ProductIQ Catalog Ground Truth Ingestion & Benchmark Store
===========================================================
Loads the 200-item expected delivery format benchmark CSV,
extracting scoped fields and attribute triples for precision scoring.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GroundTruthAttribute(BaseModel):
    label: str
    value: str
    uom: Optional[str] = None


class GroundTruthRecord(BaseModel):
    row_id: int
    mfg_part_num: str
    sku: Optional[str] = None
    part_number: Optional[str] = None
    part_desc: Optional[str] = None
    raw_manuf: Optional[str] = None
    
    # Expected Canonical Fields
    expected_manufacturer: str
    expected_brand: str
    expected_trade_name: Optional[str] = ""
    expected_mfr_part_num: str
    expected_classpath: Optional[str] = ""
    expected_product_name: Optional[str] = ""
    expected_short_desc: Optional[str] = ""
    expected_long_desc: Optional[str] = ""
    
    # Expected Attributes
    expected_attributes: List[GroundTruthAttribute] = Field(default_factory=list)
    raw_data: Dict[str, str] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "mfg_part_num": self.mfg_part_num,
            "sku": self.sku,
            "part_number": self.part_number,
            "part_desc": self.part_desc,
            "raw_manuf": self.raw_manuf,
            "expected_manufacturer": self.expected_manufacturer,
            "expected_brand": self.expected_brand,
            "expected_trade_name": self.expected_trade_name,
            "expected_mfr_part_num": self.expected_mfr_part_num,
            "expected_classpath": self.expected_classpath,
            "expected_product_name": self.expected_product_name,
            "expected_short_desc": self.expected_short_desc,
            "expected_long_desc": self.expected_long_desc,
            "expected_attributes": [a.model_dump() for a in self.expected_attributes],
        }


class GroundTruthStore:
    """
    Queryable in-memory store for expected delivery format ground truth.
    """

    def __init__(self, csv_path: Optional[Path | str] = None):
        self.path = (
            Path(csv_path)
            if csv_path
            else Path(__file__).resolve().parent.parent.parent
            / "data"
            / "catalog"
            / "ground_truth"
            / "Unihack__Expected_Output_-_Delivery_Format.csv"
        )
        self._records_by_row: Dict[int, GroundTruthRecord] = {}
        self._records_by_part: Dict[str, GroundTruthRecord] = {}
        self._all_records: List[GroundTruthRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                part_num = (row.get("Mfg_Part_Num") or row.get("MANUFACTURER_PART_NUMBER") or "").strip()
                
                # Extract up to 50 attribute triples
                attrs: List[GroundTruthAttribute] = []
                for a_idx in range(1, 51):
                    lbl_key = f"ATTRIBUTE_LABEL {a_idx}"
                    val_key = f"ATTRIBUTE_VALUE {a_idx}"
                    uom_key = f"ATTRIBUTE_UOM {a_idx}"
                    lbl = (row.get(lbl_key) or "").strip()
                    val = (row.get(val_key) or "").strip()
                    uom = (row.get(uom_key) or "").strip() or None
                    if lbl or val:
                        attrs.append(GroundTruthAttribute(label=lbl, value=val, uom=uom))

                rec = GroundTruthRecord(
                    row_id=idx,
                    mfg_part_num=part_num,
                    sku=row.get("SKU - MY_PART_NUMBER"),
                    part_number=row.get("PART_NUMBER"),
                    part_desc=row.get("Part_Desc"),
                    raw_manuf=row.get("Part_Manuf"),
                    expected_manufacturer=row.get("MANUFACTURER_NAME", ""),
                    expected_brand=row.get("BRAND_NAME", ""),
                    expected_trade_name=row.get("TRADE_NAME", ""),
                    expected_mfr_part_num=row.get("MANUFACTURER_PART_NUMBER", part_num),
                    expected_classpath=row.get("Classpath", ""),
                    expected_product_name=row.get("Product Name", ""),
                    expected_short_desc=row.get("SHORT_DESC", ""),
                    expected_long_desc=row.get("LONG_DESC1", ""),
                    expected_attributes=attrs,
                    raw_data=dict(row),
                )
                self._records_by_row[idx] = rec
                if part_num:
                    self._records_by_part[part_num.lower()] = rec
                self._all_records.append(rec)

    def count(self) -> int:
        return len(self._all_records)

    def get_by_row_id(self, row_id: int) -> Optional[GroundTruthRecord]:
        return self._records_by_row.get(row_id)

    def get_by_part_num(self, part_num: str) -> Optional[GroundTruthRecord]:
        if not part_num:
            return None
        return self._records_by_part.get(part_num.strip().lower())

    def get_all(self) -> List[GroundTruthRecord]:
        return self._all_records
