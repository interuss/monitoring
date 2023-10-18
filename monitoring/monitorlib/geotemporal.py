from __future__ import annotations

import math
from ctypes import Union
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Tuple

import arrow
from implicitdict import ImplicitDict, StringBasedTimeDelta, StringBasedDateTime
from pvlib.solarposition import get_solarposition
import s2sphere as s2sphere
from uas_standards.astm.f3411.v22a.api import Polygon
from uas_standards.astm.f3548.v21 import api as f3548v21
from uas_standards.interuss.automated_testing.scd.v1 import api as interuss_scd_api

from monitoring.monitorlib import geo
from monitoring.monitorlib.geo import LatLngPoint, Circle, Altitude, Volume3D


class OffsetTime(ImplicitDict):
    starting_from: TestTime
    """The time from which the offset should be applied."""

    offset: StringBasedTimeDelta
    """Offset from starting time."""


class NextSunPosition(ImplicitDict):
    starting_from: TestTime
    """The time after which the first time the sun is at the specified position should be found."""

    observed_from: LatLngPoint
    """The location on earth observing the sun."""

    elevation_deg: float
    """Elevation of the center of the sun above horizontal, in degrees."""


class DayOfTheWeek(str, Enum):
    Mo = "Mo"
    """Monday"""
    Tu = "Tu"
    """Tuesday"""
    We = "We"
    """Wednesday"""
    Th = "Th"
    """Thursday"""
    Fr = "Fr"
    """Friday"""
    Sa = "Sa"
    """Saturday"""
    Su = "Su"
    """Sunday"""


class NextDay(ImplicitDict):
    starting_from: TestTime
    """The time after which the first instance of one of the days should be found."""

    time_zone: str
    """Time zone in which "day" is understood.  Examples:
      * "local" (local time of machine running this code)
      * "Z" (Zulu time)
      * "-08:00" (ISO time zone)
      * "US/Pacific" (IANA time zone)"""

    days_of_the_week: Optional[List[DayOfTheWeek]] = None
    """Acceptable days of the week.  Omit to indicate that any day of the week is acceptable."""


class TestTime(ImplicitDict):
    """Exactly one of the time option fields of this object must be specified."""

    absolute_time: Optional[StringBasedDateTime] = None
    """Time option field to use a precise timestamp which does not change with test conditions.

    The value of absolute_time is limited given that the specific time a test will be started is unknown, and the jurisdictions usually impose a limit on how far in the future an operation can be planned.
    """

    start_of_test: Optional[dict] = None
    """Time option field to, if specified, use the timestamp at which the current test run started."""

    next_day: Optional[NextDay] = None
    """Time option field to use a timestamp equal to midnight beginning the next occurrence of any matching day following the specified reference timestamp."""

    next_sun_position: Optional[NextSunPosition] = None
    """Time option field to use a timestamp equal to the next time after the specified reference timestamp at which the sun will be at the specified angle above the horizon."""

    offset_from: Optional[OffsetTime] = None
    """Time option field to use a timestamp that is offset by the specified amount from the specified time."""

    use_timezone: Optional[str] = None
    """If specified, report the timestamp in the specified time zone.  Examples:
      * "local" (local time of machine running this code)
      * "Z" (Zulu time)
      * "-08:00" (ISO time zone)
      * "US/Pacific" (IANA time zone)"""


class Volume4DTemplate(ImplicitDict):
    outline_polygon: Optional[Polygon] = None
    """Polygonal 2D outline/footprint of the specified area.  May not be defined if outline_circle is defined."""

    outline_circle: Optional[Circle] = None
    """Circular outline/footprint of the specified area.  May not be defined if outline_polygon is defined."""

    start_time: Optional[TestTime] = None
    """The time at which the virtual user may start using the specified geospatial area for their flight.  May not be defined if duration and end_time are defined."""

    end_time: Optional[TestTime] = None
    """The time at which the virtual user will be finished using the specified geospatial area for their flight.  May not be defined if duration and start_time are defined."""

    duration: Optional[StringBasedTimeDelta] = None
    """If only one of start_time and end_time is specified, then the other time should be separated from the specified time by this amount.  May not be defined in both start_time and end_time are defined."""

    altitude_lower: Optional[Altitude] = None
    """The minimum altitude at which the virtual user will fly while using this volume for their flight."""

    altitude_upper: Optional[Altitude] = None
    """The maximum altitude at which the virtual user will fly while using this volume for their flight."""


_weekdays = [
    DayOfTheWeek.Mo,
    DayOfTheWeek.Tu,
    DayOfTheWeek.We,
    DayOfTheWeek.Th,
    DayOfTheWeek.Fr,
    DayOfTheWeek.Sa,
    DayOfTheWeek.Su,
]
"""Days of the week with indices corresponding with datetime.weekdays()"""


def _sun_elevation(t: datetime, lat_deg: float, lng_deg: float) -> float:
    """Compute sun elevation at the specified time and place.

    Args:
        t: Time at which to compute sun position.
        lat_deg: Latitude at which to compute sun position (degrees).
        lng_deg: Longitude at which to compute sun position (degrees).

    Returns: Degrees above the horizon of the center of the sun.
    """
    return get_solarposition(t, lat_deg, lng_deg).elevation.values[0]


class Time(StringBasedDateTime):
    def offset(self, dt: timedelta) -> Time:
        return Time(self.datetime + dt)

    def to_f3548v21(self) -> f3548v21.Time:
        return f3548v21.Time(value=self)


def resolve_time(test_time: TestTime, start_of_test: datetime) -> datetime:
    """Resolve TestTime into specific datetime."""
    result = None
    if test_time.absolute_time is not None:
        result = test_time.absolute_time.datetime
    elif test_time.start_of_test is not None:
        result = start_of_test
    elif test_time.next_day is not None:
        t0 = (
            arrow.get(resolve_time(test_time.next_day.starting_from, start_of_test))
            .to(test_time.next_day.time_zone)
            .datetime
        )
        t = datetime(
            year=t0.year, month=t0.month, day=t0.day, tzinfo=t0.tzinfo
        ) + timedelta(days=1)
        if test_time.next_day.days_of_the_week:
            allowed_weekdays = {
                _weekdays.index(d) for d in test_time.next_day.days_of_the_week
            }
            while t.weekday() not in allowed_weekdays:
                t += timedelta(days=1)
        result = t
    elif test_time.offset_from is not None:
        result = (
            resolve_time(test_time.offset_from.starting_from, start_of_test)
            + test_time.offset_from.offset.timedelta
        )
    elif test_time.next_sun_position is not None:
        t0 = resolve_time(test_time.next_sun_position.starting_from, start_of_test)

        dt = timedelta(minutes=5)
        lat = test_time.next_sun_position.observed_from.lat
        lng = test_time.next_sun_position.observed_from.lng
        el_target = test_time.next_sun_position.elevation_deg

        # Step linearly through the day looking for two adjacent times that surround the target sun elevation.
        # Note that this will fail to capture the very peak sun elevation if it is targeted.
        t2 = t0
        el2 = _sun_elevation(t2, lat, lng)
        found = False
        while t2 <= t0 + timedelta(days=1):
            t1 = t2
            el1 = el2
            t2 += dt
            el2 = _sun_elevation(t2, lat, lng)
            if (el_target > el1) != (el_target > el2):
                found = True
                break
        if not found:
            raise ValueError(
                f"Sun did not reach an elevation of {el_target} degrees between {t0} and {t2}"
            )

        # Refine time that sun elevation matches the target
        while (t2 - t1).total_seconds() > 5:
            t_m = t1 + 0.5 * (t2 - t1)
            el_m = _sun_elevation(t_m, lat, lng)
            if (el_target > el1) != (el_target > el_m):
                t2 = t_m
                el2 = el_m
            elif (el_target > el_m) != (el_target > el2):
                t1 = t_m
                el1 = el_m
            else:
                raise ValueError(
                    f"When refining sun elevation timing, the elevation target {el_target} did not appear in between t1 {t1} ({el1} degrees) and midpoint {t_m} ({el_m} degrees) nor between midpoint and t2 {t2} ({el2} degrees)"
                )

        result = t1 + 0.5 * (t2 - t1)

    if result is None:
        raise NotImplementedError(
            "TestTime did not specify a supported option for defining a time"
        )

    if test_time.use_timezone:
        result = arrow.get(result).to(test_time.use_timezone).datetime

    return result


class Volume4D(ImplicitDict):
    """Generic representation of a 4D volume, usable across multiple standards and formats."""

    volume: Volume3D
    time_start: Optional[Time] = None
    time_end: Optional[Time] = None

    def offset_time(self, dt: timedelta) -> Volume4D:
        kwargs = {"volume": self.volume}
        if self.time_start:
            kwargs["time_start"] = self.time_start.offset(dt)
        if self.time_end:
            kwargs["time_end"] = self.time_end.offset(dt)
        return Volume4D(**kwargs)

    def intersects_vol4(self, vol4_2: Volume4D) -> bool:
        vol4_1 = self
        if vol4_1.time_end.datetime < vol4_2.time_start.datetime:
            return False
        if vol4_1.time_start.datetime > vol4_2.time_end.datetime:
            return False
        return self.volume.intersects_vol3(vol4_2.volume)

    @property
    def rect_bounds(self) -> s2sphere.LatLngRect:
        lat_min = 90
        lat_max = -90
        lng_min = 360
        lng_max = -360
        if self.volume.outline_polygon:
            for v in self.volume.outline_polygon.vertices:
                lat_min = min(lat_min, v.lat)
                lat_max = max(lat_max, v.lat)
                lng_min = min(lng_min, v.lng)
                lng_max = max(lng_max, v.lng)
        if self.volume.outline_circle:
            circle = self.volume.outline_circle
            if circle.radius.units != "M":
                raise NotImplementedError(
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

    @staticmethod
    def from_values(
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        alt0: Optional[float] = None,
        alt1: Optional[float] = None,
        circle: Optional[Circle] = None,
        polygon: Optional[Polygon] = None,
    ) -> Volume4D:
        kwargs = dict()
        if circle is not None:
            kwargs["outline_circle"] = circle
        if polygon is not None:
            kwargs["outline_polygon"] = polygon
        if alt0 is not None:
            kwargs["altitude_lower"] = Altitude.w84m(alt0)
        if alt1 is not None:
            kwargs["altitude_upper"] = Altitude.w84m(alt1)
        vol3 = Volume3D(**kwargs)
        kwargs = {"volume": vol3}
        if t0 is not None:
            kwargs["time_start"] = Time(t0)
        if t1 is not None:
            kwargs["time_end"] = Time(t1)
        return Volume4D(**kwargs)

    @staticmethod
    def from_f3548v21(vol: Union[f3548v21.Volume4D, dict]) -> Volume4D:
        if not isinstance(vol, f3548v21.Volume4D) and isinstance(vol, dict):
            vol = ImplicitDict.parse(vol, f3548v21.Volume4D)
        kwargs = {"volume": Volume3D.from_f3548v21(vol.volume)}
        if "time_start" in vol and vol.time_start:
            kwargs["time_start"] = Time(vol.time_start.value)
        if "time_end" in vol and vol.time_end:
            kwargs["time_end"] = Time(vol.time_end.value)
        return Volume4D(**kwargs)

    @staticmethod
    def from_interuss_scd_api(vol: interuss_scd_api.Volume4D) -> Volume4D:
        # InterUSS SCD API is field-compatible with ASTM F3548-21
        return Volume4D.from_f3548v21(vol)

    def to_f3548v21(self) -> f3548v21.Volume4D:
        kwargs = {"volume": self.volume.to_f3548v21()}
        if "time_start" in self and self.time_start:
            kwargs["time_start"] = self.time_start.to_f3548v21()
        if "time_end" in self and self.time_end:
            kwargs["time_end"] = self.time_end.to_f3548v21()
        return f3548v21.Volume4D(**kwargs)

    def to_interuss_scd_api(self) -> interuss_scd_api.Volume4D:
        # InterUSS SCD API is field-compatible with ASTM F3548-21
        return ImplicitDict.parse(self.to_f3548v21(), interuss_scd_api.Volume4D)


def resolve_volume4d(template: Volume4DTemplate, start_of_test: datetime) -> Volume4D:
    """Resolve Volume4DTemplate into concrete Volume4D."""
    # Make 3D volume
    kwargs = {}
    if template.outline_circle is not None:
        kwargs["outline_circle"] = template.outline_circle
    if template.outline_polygon is not None:
        kwargs["outline_polygon"] = template.outline_polygon
    if template.altitude_lower is not None:
        kwargs["altitude_lower"] = template.altitude_lower
    if template.altitude_upper is not None:
        kwargs["altitude_upper"] = template.altitude_upper
    volume = Volume3D(**kwargs)

    # Make 4D volume
    kwargs = {"volume": volume}

    if template.start_time is not None:
        time_start = StringBasedDateTime(
            resolve_time(template.start_time, start_of_test)
        )
    else:
        time_start = None

    if template.end_time is not None:
        time_end = StringBasedDateTime(resolve_time(template.end_time, start_of_test))
    else:
        time_end = None

    if template.duration is not None:
        if time_start is not None and time_end is not None:
            raise ValueError(
                "A Volume4DTemplate may not specify time_start, time_end, and duration as this over-determines the time span"
            )
        if time_start is None and time_end is None:
            raise ValueError(
                "A Volume4DTemplate may not specify duration without either time_start or time_end as this under-determines the time span"
            )
        if time_start is None:
            time_start = StringBasedDateTime(
                time_end.datetime - template.duration.timedelta
            )
        if time_end is None:
            time_end = StringBasedDateTime(
                time_start.datetime + template.duration.timedelta
            )

    if time_start is not None:
        kwargs["time_start"] = time_start
    if time_end is not None:
        kwargs["time_end"] = time_end

    return Volume4D(**kwargs)


class Volume4DCollection(ImplicitDict):
    volumes: List[Volume4D]

    def __add__(self, other):
        if isinstance(other, Volume4D):
            return Volume4DCollection(volumes=self.volumes + [other])
        elif isinstance(other, Volume4DCollection):
            return Volume4DCollection(volumes=self.volumes + other.volumes)
        else:
            raise NotImplementedError(
                f"Cannot add {type(other).__name__} to {type(self).__name__}"
            )

    def __iadd__(self, other):
        if isinstance(other, Volume4D):
            self.volumes.append(other)
        elif isinstance(other, Volume4DCollection):
            self.volumes.extend(other.volumes)
        else:
            raise NotImplementedError(
                f"Cannot iadd {type(other).__name__} to {type(self).__name__}"
            )

    @property
    def time_start(self) -> Optional[Time]:
        return (
            Time(value=min(v.time_start.datetime for v in self.volumes))
            if all("time_start" in v and v.time_start for v in self.volumes)
            else None
        )

    @property
    def time_end(self) -> Optional[Time]:
        return (
            Time(value=max(v.time_end.datetime for v in self.volumes))
            if all("time_end" in v and v.time_end for v in self.volumes)
            else None
        )

    def offset_times(self, dt: timedelta) -> Volume4DCollection:
        return Volume4DCollection(volumes=[v.offset_time(dt) for v in self.volumes])

    @property
    def rect_bounds(self) -> s2sphere.LatLngRect:
        if not self.volumes:
            raise ValueError(
                "Cannot compute rectangular bounds when no volumes are present"
            )
        lat_min = math.inf
        lat_max = -math.inf
        lng_min = math.inf
        lng_max = -math.inf
        for vol4 in self.volumes:
            if "outline_polygon" in vol4.volume and vol4.volume.outline_polygon:
                for v in vol4.volume.outline_polygon.vertices:
                    lat_min = min(lat_min, v.lat)
                    lat_max = max(lat_max, v.lat)
                    lng_min = min(lng_min, v.lng)
                    lng_max = max(lng_max, v.lng)
            if "outline_circle" in vol4.volume and vol4.volume.outline_circle:
                circle = vol4.volume.outline_circle
                if circle.radius.units != "M":
                    raise NotImplementedError(
                        "Unsupported circle radius units: {}".format(
                            circle.radius.units
                        )
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

    @property
    def bounding_volume(self) -> Volume4D:
        v_min, v_max = self.meter_altitude_bounds
        rect_bound = self.rect_bounds
        lat_lo = rect_bound.lat_lo().degrees
        lng_lo = rect_bound.lng_lo().degrees
        lat_hi = rect_bound.lat_hi().degrees
        lng_hi = rect_bound.lng_hi().degrees
        kwargs = {
            "volume": Volume3D(
                altitude_lower=Altitude.w84m(v_min),
                altitude_upper=Altitude.w84m(v_max),
                outline_polygon=Polygon(
                    vertices=[
                        LatLngPoint(lat=lat_lo, lng=lng_lo),
                        LatLngPoint(lat=lat_hi, lng=lng_lo),
                        LatLngPoint(lat=lat_hi, lng=lng_hi),
                        LatLngPoint(lat=lat_lo, lng=lng_hi),
                    ]
                ),
            )
        }
        if self.time_start is not None:
            kwargs["time_start"] = self.time_start
        if self.time_end is not None:
            kwargs["time_end"] = self.time_end
        return Volume4D(**kwargs)

    @property
    def meter_altitude_bounds(self) -> Tuple[float, float]:
        alt_lo = min(
            vol4.volume.altitude_lower.value
            for vol4 in self.volumes
            if "altitude_lower" in vol4.volume
        )
        alt_hi = max(
            vol4.volume.altitude_upper.value
            for vol4 in self.volumes
            if "altitude_upper" in vol4.volume
        )
        units = [
            vol4.volume.altitude_lower.units
            for vol4 in self.volumes
            if "altitude_lower" in vol4.volume
            and vol4.volume.altitude_lower.units != "M"
        ]
        if units:
            raise NotImplementedError(
                f"altitude_lower units must currently be M; found instead {', '.join(units)}"
            )
        units = [
            vol4.volume.altitude_upper.units
            for vol4 in self.volumes
            if "altitude_upper" in vol4.volume
            and vol4.volume.altitude_upper.units != "M"
        ]
        if units:
            raise NotImplementedError(
                f"altitude_upper units must currently be M; found instead {', '.join(units)}"
            )
        return alt_lo, alt_hi

    def intersects_vol4s(self, vol4s_2: Volume4DCollection) -> bool:
        for v1 in self.volumes:
            for v2 in vol4s_2.volumes:
                if v1.intersects_vol4(v2):
                    return True
        return False

    @staticmethod
    def from_f3548v21(
        vol4s: List[Union[f3548v21.Volume4D, dict]]
    ) -> Volume4DCollection:
        volumes = [Volume4D.from_f3548v21(v) for v in vol4s]
        return Volume4DCollection(volumes=volumes)

    @staticmethod
    def from_interuss_scd_api(
        vol4s: List[interuss_scd_api.Volume4D],
    ) -> Volume4DCollection:
        volumes = [Volume4D.from_interuss_scd_api(v) for v in vol4s]
        return Volume4DCollection(volumes=volumes)

    def to_f3548v21(self) -> List[f3548v21.Volume4D]:
        return [v.to_f3548v21() for v in self.volumes]

    def to_interuss_scd_api(self) -> List[interuss_scd_api.Volume4D]:
        return [v.to_interuss_scd_api() for v in self.volumes]

    def has_active_volume(self, time_ref: datetime) -> bool:
        return any(
            vol.time_start.datetime <= time_ref <= vol.time_end.datetime
            for vol in self.volumes
        )
