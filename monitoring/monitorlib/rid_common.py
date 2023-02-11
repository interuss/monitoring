import datetime
from datetime import timedelta
from enum import Enum

import arrow

from monitoring.monitorlib import rid_v1
from monitoring.monitorlib import rid_v2

# TODO(BenjaminPelletier): Rename this file to `rid.py`


class RIDVersion(str, Enum):
    f3411_19 = "F3411-19"
    """ASTM F3411-19 (first version, v1)"""

    f3411_22a = "F3411-22a"
    """ASTM F3411-22a (second version, v2, API version 2.1)"""

    def format_time(self, t: datetime.datetime) -> str:
        return arrow.get(t).isoformat().replace("+00:00", "Z")

    @property
    def read_scope(self) -> str:
        if self == RIDVersion.f3411_19:
            return rid_v1.SCOPE_READ
        elif self == RIDVersion.f3411_22a:
            return rid_v2.SCOPE_DP
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def realtime_period(self) -> timedelta:
        if self == RIDVersion.f3411_19:
            return rid_v1.NetMaxNearRealTimeDataPeriod
        elif self == RIDVersion.f3411_22a:
            return rid_v2.NetMaxNearRealTimeDataPeriod
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def max_diagonal_km(self) -> float:
        if self == RIDVersion.f3411_19:
            return rid_v1.NetMaxDisplayAreaDiagonal
        elif self == RIDVersion.f3411_22a:
            return rid_v2.NetMaxDisplayAreaDiagonal
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def max_details_diagonal_km(self) -> float:
        if self == RIDVersion.f3411_19:
            return rid_v1.NetDetailsMaxDisplayAreaDiagonal
        elif self == RIDVersion.f3411_22a:
            return rid_v2.NetDetailsMaxDisplayAreaDiagonal
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))
