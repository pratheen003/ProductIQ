"""
Normalization Base Interface — PHASE 0 STUB

Phase 2 will implement unit conversion logic here.
"""
from abc import ABC, abstractmethod
from productiq.schema import FieldValue


class BaseNormalizer(ABC):
    """Abstract base for unit normalization transforms."""

    @abstractmethod
    def normalize(self, field_name: str, field_value: FieldValue) -> FieldValue:
        """
        Normalize a FieldValue to its canonical unit.

        Must NOT silently discard the original value.
        Must return a new FieldValue — never mutate the input.
        """
        raise NotImplementedError
