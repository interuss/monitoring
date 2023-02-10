from datetime import timedelta
from enum import Enum

from uas_standards.astm.f3411 import v19, v22a
import uas_standards.astm.f3411.v19.constants
import uas_standards.astm.f3411.v22a.constants


class RIDVersion(str, Enum):
    f3411_19 = "F3411-19"
    """ASTM F3411-19 (first version, v1)"""

    f3411_22a = "F3411-22a"
    """ASTM F3411-22a (second version, v2, API version 2.1)"""

    @property
    def read_scope(self) -> str:
        if self == RIDVersion.f3411_19:
            return v19.constants.Scope.Read
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.Scope.DisplayProvider
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def realtime_period(self) -> timedelta:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetMaxNearRealTimeDataPeriodSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetMaxNearRealTimeDataPeriodSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def max_diagonal_km(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetMaxDisplayAreaDiagonalKm
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetMaxDisplayAreaDiagonalKm
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def max_details_diagonal_km(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetDetailsMaxDisplayAreaDiagonalKm
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetDetailsMaxDisplayAreaDiagonalKm
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))
