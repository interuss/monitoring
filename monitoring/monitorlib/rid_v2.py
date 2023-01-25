import datetime
import os
from typing import Literal

from implicitdict import ImplicitDict, StringBasedDateTime
from . import rid as rid_v1


ISA_PATH = "/dss/identification_service_areas"
SUBSCRIPTION_PATH = "/dss/subscriptions"
SCOPE_DP = "rid.display_provider"
SCOPE_SP = "rid.service_provider"


# TODO(#17): Remove this variable behavior
ALTITUDE_REFERENCE: str = os.environ.get("F3411_22A_ALTITUDE_REFERENCE", "W84")
"""Altitude reference constant.

F3411-22a uses the altitude reference constant `W84`, but both the DSS and and
this repository incorrectly used `WGS84` prior to this addition.  This feature
allows prober tests to pass using an old DSS version, but can be removed once
the DSS has been updated to fix the bug.
"""


class Time(ImplicitDict):
    value: StringBasedDateTime
    format: Literal["RFC3339"]

    @classmethod
    def make(cls, t: datetime.datetime):
        return Time(format="RFC3339", value=t.strftime(DATE_FORMAT))


class Altitude(ImplicitDict):
    # TODO(#17): Change `reference` to Literal["W84"]
    reference: str
    units: Literal["M"]
    value: float

    @classmethod
    def make(cls, altitude_meters: float):
        return Altitude(reference=ALTITUDE_REFERENCE, units="M", value=altitude_meters)


MAX_SUB_PER_AREA = rid_v1.MAX_SUB_PER_AREA
MAX_SUB_TIME_HRS = rid_v1.MAX_SUB_TIME_HRS
DATE_FORMAT = rid_v1.DATE_FORMAT
NetMaxNearRealTimeDataPeriod = rid_v1.NetMaxNearRealTimeDataPeriod
NetMaxDisplayAreaDiagonal = 7  # km
NetDetailsMaxDisplayAreaDiagonal = 2  # km
geo_polygon_string = rid_v1.geo_polygon_string
