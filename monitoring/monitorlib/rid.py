from datetime import datetime, timedelta
from enum import Enum

import arrow

from monitoring.monitorlib import schema_validation
from uas_standards.astm.f3411 import v19, v22a
import uas_standards.astm.f3411.v19.api
import uas_standards.astm.f3411.v19.constants
import uas_standards.astm.f3411.v22a.api
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
            return schema_validation.F3411_19.OpenAPIPath
        elif self == RIDVersion.f3411_22a:
            return schema_validation.F3411_22a.OpenAPIPath
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

    @property
    def openapi_flights_response_path(self) -> str:
        if self == RIDVersion.f3411_19:
            return schema_validation.F3411_19.GetFlightsResponse
        elif self == RIDVersion.f3411_22a:
            return schema_validation.F3411_22a.GetFlightsResponse
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

    @property
    def openapi_flight_details_response_path(self) -> str:
        if self == RIDVersion.f3411_19:
            return schema_validation.F3411_19.GetFlightDetailsResponse
        elif self == RIDVersion.f3411_22a:
            return schema_validation.F3411_22a.GetFlightDetailsResponse
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

    @property
    def openapi_search_isas_response_path(self) -> str:
        if self == RIDVersion.f3411_19:
            return schema_validation.F3411_19.SearchIdentificationServiceAreasResponse
        elif self == RIDVersion.f3411_22a:
            return schema_validation.F3411_22a.SearchIdentificationServiceAreasResponse
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

    @property
    def openapi_get_isa_response_path(self) -> str:
        if self == RIDVersion.f3411_19:
            return schema_validation.F3411_19.GetIdentificationServiceAreaResponse
        elif self == RIDVersion.f3411_22a:
            return schema_validation.F3411_22a.GetIdentificationServiceAreaResponse
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

    @property
    def openapi_put_isa_response_path(self) -> str:
        if self == RIDVersion.f3411_19:
            return schema_validation.F3411_19.PutIdentificationServiceAreaResponse
        elif self == RIDVersion.f3411_22a:
            return schema_validation.F3411_22a.PutIdentificationServiceAreaResponse
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

    @property
    def openapi_delete_isa_response_path(self) -> str:
        if self == RIDVersion.f3411_19:
            return schema_validation.F3411_19.DeleteIdentificationServiceAreaResponse
        elif self == RIDVersion.f3411_22a:
            return schema_validation.F3411_22a.DeleteIdentificationServiceAreaResponse
        else:
            raise ValueError(f"Unsupported RID version '{self}'")

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

    @property
    def min_cluster_size_percent(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetMinClusterSizePercent
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetMinClusterSizePercent
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def min_obfuscation_distance_m(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetMinObfuscationDistanceM
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetMinObfuscationDistanceM
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def short_name(self) -> str:
        if self == RIDVersion.f3411_19:
            return "v19"
        elif self == RIDVersion.f3411_22a:
            return "v22a"
        else:
            return "unknown"

    @property
    def min_session_length_s(self) -> int:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetMinSessionLengthSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetMinSessionLengthSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def dp_init_resp_percentile95_s(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetDpInitResponse95thPercentileSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetDpInitResponse95thPercentileSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def dp_init_resp_percentile99_s(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetDpInitResponse99thPercentileSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetDpInitResponse99thPercentileSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def dp_data_resp_percentile95_s(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetDpDataResponse95thPercentileSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetDpDataResponse95thPercentileSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def dp_details_resp_percentile95_s(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetDpDetailsResponse95thPercentileSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetDpDetailsResponse95thPercentileSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def dp_details_resp_percentile99_s(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetDpDetailsResponse99thPercentileSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetDpDetailsResponse99thPercentileSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def dp_data_resp_percentile99_s(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetDpDataResponse99thPercentileSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetDpDataResponse99thPercentileSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def sp_data_resp_percentile95_s(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetSpDataResponseTime95thPercentileSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetSpDataResponseTime95thPercentileSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def sp_data_resp_percentile99_s(self) -> float:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetSpDataResponseTime99thPercentileSeconds
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetSpDataResponseTime99thPercentileSeconds
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    @property
    def dss_max_subscriptions_per_area(self) -> int:
        if self == RIDVersion.f3411_19:
            return v19.constants.NetDSSMaxSubscriptionPerArea
        elif self == RIDVersion.f3411_22a:
            return v22a.constants.NetDSSMaxSubscriptionPerArea
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))

    def flights_url_of(self, base_url: str) -> str:
        if self == RIDVersion.f3411_19:
            flights_path = v19.api.OPERATIONS[v19.api.OperationID.SearchFlights].path
            return base_url + flights_path
        elif self == RIDVersion.f3411_22a:
            flights_path = v22a.api.OPERATIONS[v22a.api.OperationID.SearchFlights].path
            return base_url + flights_path
        else:
            raise ValueError("Unsupported RID version '{}'".format(self))
