"""
ProductIQ Catalog Input Loader — Ingestion for Unihack Sample Dataset
====================================================================
Reads the 1,000-row raw catalog input CSV, applies global placeholder
filtering, and exposes strongly-typed queryable rows.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional
from productiq_catalog.schema.models import CatalogInputRow
from productiq_catalog.lookups.loader import clean_string


class InputDatasetLoader:
    """
    Queryable loader for Unihack__Sample_Dataset_-_Input.csv.
    """

    def __init__(self, csv_path: Optional[Path | str] = None):
        self.path = (
            Path(csv_path)
            if csv_path
            else Path(__file__).resolve().parent.parent.parent
            / "data"
            / "catalog"
            / "input"
            / "Unihack__Sample_Dataset_-_Input.csv"
        )
        self._rows: List[CatalogInputRow] = []
        self._by_id: Dict[int, CatalogInputRow] = {}
        self._by_part: Dict[str, CatalogInputRow] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                part_num = (row.get("Mfg_Part_Num") or "").strip()
                item = CatalogInputRow(
                    row_id=idx,
                    mfg_part_num=part_num,
                    part_desc=(row.get("Part_Desc") or "").strip(),
                    e1_brand=clean_string(row.get("E1_Brand")),
                    unilog_brand=clean_string(row.get("Unilog_Brand")),
                    dib_brand=clean_string(row.get("DIB_Brand")),
                    part_manuf=clean_string(row.get("Part_Manuf")),
                )
                self._rows.append(item)
                self._by_id[idx] = item
                if part_num:
                    self._by_part[part_num.lower()] = item

    def count(self) -> int:
        return len(self._rows)

    def get_all(self) -> List[CatalogInputRow]:
        return self._rows

    def get_by_row_id(self, row_id: int) -> Optional[CatalogInputRow]:
        return self._by_id.get(row_id)

    def get_by_part_num(self, part_num: str) -> Optional[CatalogInputRow]:
        if not part_num:
            return None
        return self._by_part.get(part_num.strip().lower())
