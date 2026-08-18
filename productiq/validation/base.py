"""
Validation Base Interface — PHASE 0 STUB
"""
from abc import ABC, abstractmethod
from productiq.schema import MotorProduct


class BaseValidator(ABC):
    """Abstract base for engineering plausibility validators."""

    @abstractmethod
    def validate(self, product: MotorProduct) -> MotorProduct:
        """
        Run validation checks on a motor product.

        Must return an updated MotorProduct with any implausible fields
        set to status=Conflicted with an explanatory SourceEntry.
        Must NOT silently modify values without recording provenance.
        """
        raise NotImplementedError
