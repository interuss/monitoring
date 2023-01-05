import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Literal
from implicitdict import ImplicitDict, StringBasedDateTime

import arrow
import s2sphere
import shapely.geometry

from monitoring.monitorlib import geo


TIME_FORMAT_CODE = "RFC3339"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
EARTH_CIRCUMFERENCE_M = 40.075e6

# API version 0.3.17 is programmatically identical to version 1.0.0, so both these versions can be used interchangeably.
API_1_0_0 = "1.0.0"
API_0_3_17 = API_1_0_0

SCOPE_SC = "utm.strategic_coordination"
SCOPE_CM = "utm.constraint_management"
SCOPE_CP = "utm.constraint_processing"
SCOPE_CM_SA = "utm.conformance_monitoring_sa"
SCOPE_AA = "utm.availability_arbitration"

NO_OVN_PHRASES = {"", "Available from USS"}


def latitude_degrees(distance_meters: float) -> float:
    return 360 * distance_meters / EARTH_CIRCUMFERENCE_M


def parse_time(time: Dict) -> datetime:
    t_str = time["value"]
    return arrow.get(t_str).datetime


def offset_time(vol4s: List[Dict], dt: timedelta) -> List[Dict]:
    for vol4 in vol4s:
        vol4["time_start"] = make_time(parse_time(vol4["time_start"]) + dt)
        vol4["time_end"] = make_time(parse_time(vol4["time_end"]) + dt)
    return vol4s


class Subscription(dict):
    @property
    def valid(self) -> bool:
        if self.version is None:
            return False
        return True

    @property
    def version(self) -> Optional[str]:
        return self.get("version", None)


################################################################################
#################### Start of ASTM-standard definitions    #####################
#################### interfaces/astm-utm/Protocol/utm.yaml #####################
################################################################################


class LatLngPoint(ImplicitDict):
    """A class to hold information about a location as Latitude / Longitude pair"""

    lat: float
    lng: float


class Radius(ImplicitDict):
    """A class to hold the radius of a circle for the outline_circle object"""

    value: float
    units: str


class Polygon(ImplicitDict):
    """A class to hold the polygon object, used in the outline_polygon of the Volume3D object"""

    vertices: List[LatLngPoint]  # A minimum of three LatLngPoints are required


class Circle(ImplicitDict):
    """A class the details of a circle object used in the outline_circle object"""

    center: LatLngPoint
    radius: Radius


class Altitude(ImplicitDict):
    """A class to hold altitude information"""

    value: float
    reference: Literal["W84"]
    units: str


class Time(ImplicitDict):
    """A class to hold Time details"""

    value: StringBasedDateTime
    format: Literal["RFC3339"]


class Volume3D(ImplicitDict):
    """A class to hold Volume3D objects"""

    outline_circle: Optional[Circle]
    outline_polygon: Optional[Polygon]
    altitude_lower: Optional[Altitude]
    altitude_upper: Optional[Altitude]


class Volume4D(ImplicitDict):
    """A class to hold Volume4D objects"""

    volume: Volume3D
    time_start: Optional[Time]
    time_end: Optional[Time]


class OperationalIntentReference(ImplicitDict):
    id: str
    manager: str
    uss_availability: str
    version: int
    state: str
    ovn: str
    time_start: Time
    time_end: Time
    uss_base_url: str
    subscription_id: str


class ErrorResponse(ImplicitDict):
    message: str


class QueryOperationalIntentReferenceParameters(ImplicitDict):
    area_of_interest: Volume4D


class QueryOperationalIntentReferenceResponse(ImplicitDict):
    operational_intent_references: List[OperationalIntentReference]


class ImplicitSubscriptionParameters(ImplicitDict):
    uss_base_url: str
    notify_for_constraints: Optional[bool]


class PutOperationalIntentReferenceParameters(ImplicitDict):
    extents: Volume4D
    key: List[str]
    state: str
    uss_base_url: str
    subscription_id: Optional[str]
    new_subscription: Optional[ImplicitSubscriptionParameters]


class SubscriptionState(ImplicitDict):
    subscription_id: str
    notification_index: int


class SubscriberToNotify(ImplicitDict):
    uss_base_url: str
    subscriptions: List[SubscriptionState]


class ChangeOperationalIntentReferenceResponse(ImplicitDict):
    subscribers: List[SubscriberToNotify]
    operational_intent_reference: OperationalIntentReference


class OperationalIntentDetails(ImplicitDict):
    volumes: List[Volume4D]
    off_nominal_volumes: List[Volume4D]
    priority: int


class OperationalIntent(ImplicitDict):
    reference: OperationalIntentReference
    details: OperationalIntentDetails


class GetOperationalIntentDetailsResponse(ImplicitDict):
    operational_intent: OperationalIntent


class PutOperationalIntentDetailsParameters(ImplicitDict):
    operational_intent_id: str
    operational_intent: Optional[OperationalIntent]
    subscriptions: List[SubscriptionState]


################################################################################
#################### End of ASTM-standard definitions    #####################
#################### interfaces/astm-utm/Protocol/utm.yaml #####################
################################################################################


class DeleteAllFlightsRequest(ImplicitDict):
    extents: List[Volume4D]


def make_vol4(
    t0: Optional[datetime] = None,
    t1: Optional[datetime] = None,
    alt0: Optional[float] = None,
    alt1: Optional[float] = None,
    circle: Dict = None,
    polygon: Dict = None,
) -> Volume4D:
    kwargs = dict()
    if circle is not None:
        kwargs["outline_circle"] = circle
    if polygon is not None:
        kwargs["outline_polygon"] = polygon
    if alt0 is not None:
        kwargs["altitude_lower"] = make_altitude(alt0)
    if alt1 is not None:
        kwargs["altitude_upper"] = make_altitude(alt1)
    vol3 = Volume3D(**kwargs)
    kwargs = {"volume": vol3}
    if t0 is not None:
        kwargs["time_start"] = make_time(t0)
    if t1 is not None:
        kwargs["time_end"] = make_time(t1)
    return Volume4D(**kwargs)


def make_time(t: datetime) -> Time:
    s = t.isoformat()
    if t.tzinfo is None:
        s += "Z"
    return Time(value=StringBasedDateTime(s), format="RFC3339")


def make_altitude(alt_meters: float) -> Altitude:
    return Altitude(value=alt_meters, reference="W84", units="M")


def make_circle(lat: float, lng: float, radius: float) -> Circle:
    return Circle(
        center=LatLngPoint(lat=lat, lng=lng), radius=Radius(value=radius, units="M")
    )


def make_polygon(
    coords: List[Tuple[float, float]] = None, latlngrect: s2sphere.LatLngRect = None
) -> Polygon:
    if coords is not None:
        return Polygon(
            vertices=[LatLngPoint(lat=lat, lng=lng) for (lat, lng) in coords]
        )

    return Polygon(
        vertices=[
            LatLngPoint(
                lat=latlngrect.lat_lo().degrees, lng=latlngrect.lng_lo().degrees
            ),
            LatLngPoint(
                lat=latlngrect.lat_lo().degrees, lng=latlngrect.lng_hi().degrees
            ),
            LatLngPoint(
                lat=latlngrect.lat_hi().degrees, lng=latlngrect.lng_hi().degrees
            ),
            LatLngPoint(
                lat=latlngrect.lat_hi().degrees, lng=latlngrect.lng_lo().degrees
            ),
        ]
    )


def start_of(vol4s: List[Volume4D]) -> datetime:
    return min([parse_time(vol4["time_start"]) for vol4 in vol4s])


def end_of(vol4s: List[Volume4D]) -> datetime:
    return max([parse_time(vol4["time_end"]) for vol4 in vol4s])


def rect_bounds_of(vol4s: List[Volume4D]) -> s2sphere.LatLngRect:
    lat_min = 90
    lat_max = -90
    lng_min = 360
    lng_max = -360
    for vol4 in vol4s:
        if "outline_polygon" in vol4.volume:
            for v in vol4.volume.outline_polygon.vertices:
                lat_min = min(lat_min, v.lat)
                lat_max = max(lat_max, v.lat)
                lng_min = min(lng_min, v.lng)
                lng_max = max(lng_max, v.lng)
        if "outline_circle" in vol4.volume:
            circle = vol4.volume.outline_circle
            if circle.radius.units != "M":
                raise ValueError(
                    "Unsupported circle radius units: {}".format(circle.radius.units)
                )
            lat_radius = 360 * circle.radius.value / geo.EARTH_CIRCUMFERENCE_M
            lng_radius = (
                360
                * circle.radius.value
                / (geo.EARTH_CIRCUMFERENCE_M * math.cos(math.radians(lat_radius)))
            )
            lat_min = min(lat_min, circle.center.lat - lat_radius)
            lat_max = max(lat_max, circle.center.lat + lat_radius)
            lng_min = min(lng_min, circle.center.lng - lng_radius)
            lng_max = max(lng_max, circle.center.lng + lng_radius)
    p1 = s2sphere.LatLng.from_degrees(lat_min, lng_min)
    p2 = s2sphere.LatLng.from_degrees(lat_max, lng_max)
    return s2sphere.LatLngRect.from_point_pair(p1, p2)


def meter_altitude_bounds_of(vol4s: List[Volume4D]) -> Tuple[float, float]:
    alt_lo = min(
        vol4.volume.altitude_lower.value
        for vol4 in vol4s
        if "altitude_lower" in vol4.volume
    )
    alt_hi = max(
        vol4.volume.altitude_upper.value
        for vol4 in vol4s
        if "altitude_upper" in vol4.volume
    )
    units = [
        vol4.volume.altitude_lower.units
        for vol4 in vol4s
        if "altitude_lower" in vol4.volume and vol4.volume.altitude_lower.units != "M"
    ]
    if units:
        raise ValueError(
            f"altitude_lower units must always be M; found instead {', '.join(units)}"
        )
    units = [
        vol4.volume.altitude_upper.units
        for vol4 in vol4s
        if "altitude_upper" in vol4.volume and vol4.volume.altitude_upper.units != "M"
    ]
    if units:
        raise ValueError(
            f"altitude_upper units must always be M; found instead {', '.join(units)}"
        )
    return alt_lo, alt_hi


def bounding_vol4(vol4s: List[Volume4D]) -> Volume4D:
    t_start = start_of(vol4s)
    t_end = end_of(vol4s)
    v_min, v_max = meter_altitude_bounds_of(vol4s)
    rect_bound = rect_bounds_of(vol4s)
    lat_lo = rect_bound.lat_lo().degrees
    lng_lo = rect_bound.lng_lo().degrees
    lat_hi = rect_bound.lat_hi().degrees
    lng_hi = rect_bound.lng_hi().degrees
    return Volume4D(
        time_start=make_time(t_start),
        time_end=make_time(t_end),
        volume=Volume3D(
            altitude_lower=make_altitude(v_min),
            altitude_upper=make_altitude(v_max),
            outline_polygon=Polygon(
                vertices=[
                    LatLngPoint(lat=lat_lo, lng=lng_lo),
                    LatLngPoint(lat=lat_hi, lng=lng_lo),
                    LatLngPoint(lat=lat_hi, lng=lng_hi),
                    LatLngPoint(lat=lat_lo, lng=lng_hi),
                ]
            ),
        ),
    )


def vol4_intersect(vol4_1: Volume4D, vol4_2: Volume4D) -> bool:
    if parse_time(vol4_1.time_end) < parse_time(vol4_2.time_start):
        return False
    if parse_time(vol4_1.time_start) > parse_time(vol4_2.time_end):
        return False
    if vol4_1.volume.altitude_upper.value < vol4_2.volume.altitude_lower.value:
        return False
    if vol4_1.volume.altitude_lower.value > vol4_2.volume.altitude_upper.value:
        return False

    if "outline_circle" in vol4_1.volume:
        circle = vol4_1.volume.outline_circle
        if circle.radius.units != "M":
            raise ValueError(
                "Unsupported circle radius units: {}".format(circle.radius.units)
            )
        ref = s2sphere.LatLng.from_degrees(circle.center.lat, circle.center.lng)
        footprint1 = shapely.geometry.Point(0, 0).buffer(
            vol4_1.volume.outline_circle.radius.value
        )
    elif "outline_polygon" in vol4_1.volume:
        p = vol4_1.volume.outline_polygon.vertices[0]
        ref = s2sphere.LatLng.from_degrees(p.lat, p.lng)
        footprint1 = shapely.geometry.Polygon(
            geo.flatten(ref, s2sphere.LatLng.from_degrees(v.lat, v.lng))
            for v in vol4_1.volume.outline_polygon.vertices
        )
    else:
        raise ValueError("Neither outline_circle nor outline_polygon specified")

    if "outline_circle" in vol4_2.volume:
        circle = vol4_2.volume.outline_circle
        if circle.radius.units != "M":
            raise ValueError(
                "Unsupported circle radius units: {}".format(circle.radius.units)
            )
        xy = geo.flatten(
            ref, s2sphere.LatLng.from_degrees(circle.center.lat, circle.center.lng)
        )
        footprint2 = shapely.geometry.Point(*xy).buffer(circle.radius.value)
    elif "outline_polygon" in vol4_1.volume:
        footprint2 = shapely.geometry.Polygon(
            geo.flatten(ref, s2sphere.LatLng.from_degrees(v.lat, v.lng))
            for v in vol4_2.volume.outline_polygon.vertices
        )
    else:
        raise ValueError("Neither outline_circle nor outline_polygon specified")

    return footprint1.intersects(footprint2)


def vol4s_intersect(vol4s_1: List[Volume4D], vol4s_2: List[Volume4D]) -> bool:
    for v1 in vol4s_1:
        for v2 in vol4s_2:
            if vol4_intersect(v1, v2):
                return True
    return False
