import datetime

import s2sphere
from uas_standards.astm.f3411.v22a.api import Time, Altitude, Polygon, LatLngPoint

from . import rid_v1 as rid_v1


def make_time(t: datetime.datetime) -> Time:
    return Time(format="RFC3339", value=t.strftime(DATE_FORMAT))


def make_altitude(altitude_meters: float) -> Altitude:
    return Altitude(reference="W84", units="M", value=altitude_meters)


def make_polygon_outline(area: s2sphere.LatLngRect) -> Polygon:
    return Polygon(
        vertices=[
            LatLngPoint(lat=area.lat_lo().degrees, lng=area.lng_lo().degrees),
            LatLngPoint(lat=area.lat_lo().degrees, lng=area.lng_hi().degrees),
            LatLngPoint(lat=area.lat_hi().degrees, lng=area.lng_hi().degrees),
            LatLngPoint(lat=area.lat_hi().degrees, lng=area.lng_lo().degrees),
        ]
    )


DATE_FORMAT = rid_v1.DATE_FORMAT
geo_polygon_string = rid_v1.geo_polygon_string
