from __future__ import annotations
from abc import ABC, abstractmethod
import inspect
import sys
from typing import TypeVar

LocalityCode = str
"""Case-sensitive string naming a subclass of the Locality base class"""


class Locality(ABC):
    _NOT_IMPLEMENTED_MSG = "All methods of base Locality class must be implemented by each specific subclass"

    @classmethod
    def locality_code(cls) -> str:
        raise NotImplementedError(
            "locality_code classmethod must be overridden by each specific subclass"
        )

    @abstractmethod
    def is_uspace_applicable(self) -> bool:
        """Returns true iff U-space rules apply to this locality"""
        raise NotImplementedError(Locality._NOT_IMPLEMENTED_MSG)

    @abstractmethod
    def allows_same_priority_intersections(self, priority: int) -> bool:
        """Returns true iff locality allows intersections between two operations at this priority level for ASTM F3548-21"""
        raise NotImplementedError(Locality._NOT_IMPLEMENTED_MSG)

    def __str__(self):
        return self.__class__.__name__

    @staticmethod
    def from_locale(locality_code: LocalityCode) -> LocalityType:
        current_module = sys.modules[__name__]
        for name, obj in inspect.getmembers(current_module, inspect.isclass):
            if issubclass(obj, Locality) and obj != Locality:
                if obj.locality_code() == locality_code:
                    return obj()
        raise ValueError(
            f"Could not find Locality implementation for Locality code '{locality_code}' (expected to find a subclass of the Locality astract base class where classmethod locality_code returns '{locality_code}')"
        )


LocalityType = TypeVar("LocalityType", bound=Locality)


class Switzerland(Locality):
    @classmethod
    def locality_code(cls) -> str:
        return "CHE"

    def is_uspace_applicable(self) -> bool:
        return True

    def allows_same_priority_intersections(self, priority: int) -> bool:
        return False


class UnitedStatesIndustryCollaboration(Locality):
    @classmethod
    def locality_code(cls) -> str:
        return "US.IndustryCollaboration"

    def is_uspace_applicable(self) -> bool:
        return False

    def allows_same_priority_intersections(self, priority: int) -> bool:
        return False
