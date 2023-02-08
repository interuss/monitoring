import datetime

from uas_standards.astm.f3411.v22a.api import Time, Altitude
from . import rid_v1 as rid_v1


ISA_PATH = "/dss/identification_service_areas"
SUBSCRIPTION_PATH = "/dss/subscriptions"
SCOPE_DP = "rid.display_provider"
SCOPE_SP = "rid.service_provider"


def make_time(t: datetime.datetime) -> Time:
    return Time(format="RFC3339", value=t.strftime(DATE_FORMAT))


def make_altitude(altitude_meters: float) -> Altitude:
    return Altitude(reference="W84", units="M", value=altitude_meters)


MAX_SUB_PER_AREA = rid_v1.MAX_SUB_PER_AREA
MAX_SUB_TIME_HRS = rid_v1.MAX_SUB_TIME_HRS
DATE_FORMAT = rid_v1.DATE_FORMAT
NetMaxNearRealTimeDataPeriod = rid_v1.NetMaxNearRealTimeDataPeriod
NetMaxDisplayAreaDiagonal = 7  # km
NetDetailsMaxDisplayAreaDiagonal = 2  # km
geo_polygon_string = rid_v1.geo_polygon_string
