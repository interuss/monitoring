from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List

import arrow
from implicitdict import ImplicitDict, StringBasedTimeDelta, StringBasedDateTime
from pvlib.solarposition import get_solarposition
from monitoring.monitorlib.geo import LatLngPoint
from monitoring.monitorlib.scd import Polygon, Circle, Altitude, Volume3D, Volume4D


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
