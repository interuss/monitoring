import datetime
from typing import List, Optional

import s2sphere
from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.astm.f3411.v22a.api import (
    Time,
    Altitude,
    LatLngPoint,
    Volume4D,
)

from . import rid_v1 as rid_v1


def make_time(t: datetime.datetime) -> Time:
    return Time(format="RFC3339", value=StringBasedDateTime(t))


def make_altitude(altitude_meters: float) -> Altitude:
    return Altitude(reference="W84", units="M", value=altitude_meters)


def make_lat_lng_point(lat: float, lng: float) -> LatLngPoint:
    return LatLngPoint(lat=lat, lng=lng)


def make_lat_lng_point_from_s2(point: s2sphere.LatLng) -> LatLngPoint:
    return make_lat_lng_point(point.lat().degrees, point.lng().degrees)


def make_volume_4d(
    vertices: List[s2sphere.LatLng],
    alt_lo: float,
    alt_hi: float,
    start_time: Optional[datetime.datetime],
    end_time: Optional[datetime.datetime],
) -> Volume4D:
    return ImplicitDict.parse(
        {
            "volume": {
                "outline_polygon": {
                    "vertices": [
                        {"lat": vertex.lat().degrees, "lng": vertex.lng().degrees}
                        for vertex in vertices
                    ],
                },
                "altitude_lower": make_altitude(alt_lo),
                "altitude_upper": make_altitude(alt_hi),
            },
            **({"time_start": make_time(start_time)} if start_time is not None else {}),
            **({"time_end": make_time(end_time)} if end_time is not None else {}),
        },
        Volume4D,
    )


DATE_FORMAT = rid_v1.DATE_FORMAT
geo_polygon_string = rid_v1.geo_polygon_string
geo_polygon_string_from_s2 = rid_v1.geo_polygon_string_from_s2
