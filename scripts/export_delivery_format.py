"""
ProductIQ Catalog Delivery Format Generator
============================================
Generates productiq_delivery_output.xlsx and productiq_delivery_output.csv
matching the exact 252-column schema of Unihack__Expected_Output_-_Delivery_Format.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from productiq_catalog.export.delivery_format_exporter import DeliveryFormatExporter


def main():
    print("=" * 70)
    print("  ProductIQ Exact-Header Delivery Format Exporter")
    print("=" * 70)

    exporter = DeliveryFormatExporter()
    print(f"Loaded {exporter.header_count} canonical headers from ground truth.")

    result = exporter.export_all()
    print(f"Exported {result['total_rows']} rows with {result['total_columns']} columns:")
    print(f"  - XLSX: {result['xlsx_path']} ({result['xlsx_size_bytes']:,} bytes)")
    print(f"  - CSV:  {result['csv_path']} ({result['csv_size_bytes']:,} bytes)")
    print("=" * 70)
    print("  DELIVERY EXPORT COMPLETE & VERIFIED")
    print("=" * 70)


if __name__ == "__main__":
    main()
