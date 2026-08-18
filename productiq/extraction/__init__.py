"""
ProductIQ Extraction Package — Phase 1
=======================================
Public API for the extraction layer.

Usage:
    from productiq.extraction import PDFExtractor, CSVExtractor, WebExtractor
    from productiq.extraction.models import EvidenceRecord, ExtractionResult
"""
from productiq.extraction.models import (
    BatchExtractionSummary,
    EvidenceRecord,
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
)
from productiq.extraction.pdf_extractor import PDFExtractor
from productiq.extraction.csv_extractor import CSVExtractor
from productiq.extraction.web_extractor import WebExtractor, extract_web_source

__all__ = [
    # Models
    "EvidenceRecord",
    "ExtractionResult",
    "ExtractionStatus",
    "ExtractionMethod",
    "BatchExtractionSummary",
    # Extractors
    "PDFExtractor",
    "CSVExtractor",
    "WebExtractor",
    "extract_web_source",
]
