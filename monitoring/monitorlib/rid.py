from datetime import datetime, timedelta
from enum import Enum

import arrow

from monitoring.monitorlib import schema_validation
from uas_standards.astm.f3411 import v19, v22a
import uas_standards.astm.f3411.v19.constants
import uas_standards.astm.f3411.v22a.constants


class RIDVersion(str, Enum):
    f3411_19 = "F3411-19"
    """ASTM F3411-19 (first version, v1)"""

    f3411_22a = "F3411-22a"
    """ASTM F3411-22a (second version, v2, API version 2.1)"""

    def format_time(self, t: datetime) -> str:
        return arrow.get(t).isoformat().replace("+00:00", "Z")

    @property
    def openapi_path(self) -> str:
        if self == RIDVersion.f3411_19:
            return schema_validation.OPENAPI_F3411_19
        elif self == RIDVersion.f3411_22a:
            return schema_validation.OPENAPI_F3411_22A
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

    @property
    def openapi_flights_response_path(self) -> str:
        if self == RIDVersion.f3411_19:
            return "components.schemas.GetFlightsResponse"
        elif self == RIDVersion.f3411_22a:
            return "components.schemas.GetFlightsResponse"
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

    @property
    def openapi_flight_details_response_path(self) -> str:
        if self == RIDVersion.f3411_19:
            return "components.schemas.GetFlightDetailsResponse"
        elif self == RIDVersion.f3411_22a:
            return "components.schemas.GetFlightDetailsResponse"
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

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
            return timedelta(seconds=v19.constants.NetMaxNearRealTimeDataPeriodSeconds)
        elif self == RIDVersion.f3411_22a:
            return timedelta(seconds=v22a.constants.NetMaxNearRealTimeDataPeriodSeconds)
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
