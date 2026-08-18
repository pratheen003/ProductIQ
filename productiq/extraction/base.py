"""
Base Extractor Interface
------------------------
PHASE 0 STUB — defines the contract that Phase 1 extractors must implement.

All extractors must:
1. Accept a source file path or URL
2. Return a list of (field_name, FieldValue) tuples
3. Always include a populated SourceEntry in the FieldValue.sources list
4. Never return a FieldValue with an empty sources list for extracted data
5. Never silently discard a value — if two passes yield different values,
   return both as separate FieldValue observations for conflict detection
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple

from productiq.schema import FieldValue, SourceEntry


class BaseExtractor(ABC):
    """Abstract base class for all ProductIQ source extractors."""

    @abstractmethod
    def extract(self, source_path: Path, source_entry: SourceEntry) -> List[Tuple[str, FieldValue]]:
        """
        Extract motor field observations from a source.

        Args:
            source_path: Path to the source file (PDF, HTML, CSV, etc.)
            source_entry: Pre-populated SourceEntry describing the source document.

        Returns:
            List of (field_name, FieldValue) tuples.
            field_name must correspond to a MotorProduct attribute name.
            FieldValue.sources must include the provided source_entry.
        """
        raise NotImplementedError


# Phase 1 will implement:
# - PDFExtractor(BaseExtractor)
# - WebExtractor(BaseExtractor)
# - CSVExtractor(BaseExtractor)
