"""
ProductIQ Phase 1 — Batch Extraction Script
=============================================
Run: python scripts/run_extraction.py

Loads dataset_manifest.json, runs all three extractors over every product,
saves raw evidence to data/processed/<product_id>/, and prints a summary.

Exit codes:
  0 — All sources attempted, output written
  1 — Fatal error (manifest not found, output dir not writable, etc.)

Note: Individual source failures do NOT cause exit code 1.
The script continues and reports failures in the summary.
"""
import json
import logging
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from productiq.logging_setup import setup_logging
from productiq.config import load_config
from productiq.extraction import (
    PDFExtractor,
    CSVExtractor,
    WebExtractor,
    BatchExtractionSummary,
    ExtractionStatus,
)

setup_logging("INFO")
logger = logging.getLogger("productiq.scripts.run_extraction")

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"


def load_manifest(data_dir: Path) -> list:
    manifest_path = data_dir / "dataset_manifest.json"
    if not manifest_path.exists():
        logger.error("Manifest not found: %s", manifest_path)
        sys.exit(1)
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def ensure_output_dir(processed_dir: Path, product_id: str) -> Path:
    out = processed_dir / product_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def save_evidence(out_dir: Path, source_type: str, result) -> None:
    filename = f"{source_type}_evidence.json"
    path = out_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(result.to_json(indent=2))


def main():
    config = load_config()
    data_dir = Path(config.data_dir)
    processed_dir = data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    print()
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  ProductIQ Phase 1 Extraction{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print()

    # --- Load manifest ---
    manifest = load_manifest(data_dir)
    manifest_by_id = {p["product_id"]: p for p in manifest}
    summary = BatchExtractionSummary(products_discovered=len(manifest))
    print(f"  Products discovered: {len(manifest)}")
    print()

    # =================================================================
    # PDF EXTRACTION — one extractor over the entire PDF
    # =================================================================
    pdf_path = data_dir / "pdf" / "WEG_W22_Severe_Process_IE3_Brochure.pdf"
    pdf_source_id = "WEG_W22_Severe_Process_IE3_Brochure"

    pdf_extractor = PDFExtractor(
        pdf_path=pdf_path,
        source_id=pdf_source_id,
        manifest_products=manifest_by_id,
    )
    pdf_results = pdf_extractor.extract_all()

    # Organise PDF results by product
    pdf_by_product = {r.product_id: r for r in pdf_results}
    pdf_total_evidence = sum(r.evidence_count for r in pdf_results)

    for entry in manifest:
        pid = entry["product_id"]
        summary.pdf_attempted += 1
        result = pdf_by_product.get(pid)
        if result and result.status == ExtractionStatus.SUCCESS.value:
            summary.pdf_succeeded += 1
            out_dir = ensure_output_dir(processed_dir, pid)
            save_evidence(out_dir, "pdf", result)
        else:
            summary.pdf_failed += 1
            # Save the failed result too (for diagnostics)
            if result:
                out_dir = ensure_output_dir(processed_dir, pid)
                save_evidence(out_dir, "pdf", result)
            else:
                logger.warning("PDF: no result for product %s", pid)

    # Also save any UNKNOWN/GLOBAL evidence from PDF
    for pid, result in pdf_by_product.items():
        if pid not in manifest_by_id:
            out_dir = ensure_output_dir(processed_dir, pid)
            save_evidence(out_dir, "pdf", result)

    # =================================================================
    # CSV EXTRACTION
    # =================================================================
    csv_path = data_dir / "csv" / "legacy_motors.csv"
    csv_source_id = "legacy_motors_csv_weg_w22sp_derived"

    csv_extractor = CSVExtractor(
        csv_path=csv_path,
        source_id=csv_source_id,
        manifest_products=manifest_by_id,
    )
    csv_results = csv_extractor.extract_all()
    csv_by_product = {r.product_id: r for r in csv_results}

    for entry in manifest:
        pid = entry["product_id"]
        summary.csv_attempted += 1
        result = csv_by_product.get(pid)
        if result and result.status == ExtractionStatus.SUCCESS.value:
            summary.csv_succeeded += 1
            out_dir = ensure_output_dir(processed_dir, pid)
            save_evidence(out_dir, "csv", result)
        else:
            summary.csv_failed += 1
            if result:
                out_dir = ensure_output_dir(processed_dir, pid)
                save_evidence(out_dir, "csv", result)
            else:
                logger.warning("CSV: no result for product %s", pid)

    # =================================================================
    # WEB EXTRACTION
    # =================================================================
    web_dir = data_dir / "web"

    for entry in manifest:
        pid = entry["product_id"]
        web_info = entry.get("web", {})
        web_file_rel = web_info.get("file", "")
        web_source_ref = web_info.get("source", "")

        summary.web_attempted += 1

        if not web_file_rel:
            summary.web_failed += 1
            logger.warning("Web: no file reference for %s", pid)
            continue

        url_file = data_dir / web_file_rel
        web_source_id = f"web_{pid}"

        extractor = WebExtractor(
            url_file=url_file,
            source_id=web_source_id,
            product_id=pid,
        )
        result = extractor.extract()
        out_dir = ensure_output_dir(processed_dir, pid)
        save_evidence(out_dir, "web", result)

        if result.status == ExtractionStatus.SUCCESS.value:
            summary.web_succeeded += 1
        elif result.status == ExtractionStatus.PARTIAL.value:
            summary.web_succeeded += 1   # partial counts as attempted+processed
        else:
            summary.web_failed += 1

    # =================================================================
    # Summary
    # =================================================================
    all_results = list(pdf_by_product.values()) + csv_results
    summary.total_evidence = sum(r.evidence_count for r in all_results)

    # Save global summary
    summary_path = processed_dir / "extraction_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary.to_dict(), f, indent=2)

    # Print summary
    print(f"  {'Source':<8} {'Attempted':>10} {'Succeeded':>10} {'Failed':>8}")
    print(f"  {'-'*40}")
    print(f"  {'PDF':<8} {summary.pdf_attempted:>10} {summary.pdf_succeeded:>10} {summary.pdf_failed:>8}")
    print(f"  {'CSV':<8} {summary.csv_attempted:>10} {summary.csv_succeeded:>10} {summary.csv_failed:>8}")
    print(f"  {'Web':<8} {summary.web_attempted:>10} {summary.web_succeeded:>10} {summary.web_failed:>8}")
    print()
    print(f"  Evidence records: {summary.total_evidence}")
    print(f"  Output: {processed_dir}")
    print()
    print(f"{BOLD}{'='*60}{RESET}")

    any_success = (
        summary.pdf_succeeded > 0
        or summary.csv_succeeded > 0
        or summary.web_succeeded > 0
    )
    if any_success:
        print(f"{BOLD}{GREEN}  PHASE 1 EXTRACTION: COMPLETE{RESET}")
    else:
        print(f"{BOLD}{RED}  PHASE 1 EXTRACTION: INCOMPLETE — no sources succeeded{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print()

    sys.exit(0 if any_success else 1)


if __name__ == "__main__":
    main()
