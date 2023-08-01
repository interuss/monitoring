from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List

from implicitdict import ImplicitDict, StringBasedTimeDelta, StringBasedDateTime
from monitoring.monitorlib.scd import Polygon, Circle, Altitude, Volume3D, Volume4D


class OffsetTime(ImplicitDict):
    starting_from: TestTime
    """The time from which the offset should be applied."""

    offset: StringBasedTimeDelta
    """Offset from starting time."""


class NextSunPosition(ImplicitDict):
    starting_from: TestTime
    """The time after which the first time the sun is at the specified position should be found."""

    elevation_deg: float
    """Elevation of the sun above horizontal, in degrees."""


class DayOfTheWeek(str, Enum):
    M = "M"
    """Monday"""
    T = "T"
    """Tuesday"""
    W = "W"
    """Wednesday"""
    Th = "Th"
    """Thursday"""
    F = "F"
    """Friday"""
    Sa = "Sa"
    """Saturday"""
    Su = "Su"
    """Sunday"""


class NextDay(ImplicitDict):
    starting_from: TestTime
    """The time after which the first instance of one of the days should be found."""

    days_of_the_week: Optional[List[DayOfTheWeek]] = None
    """Acceptable days of the week.  Omit to indicate that any day of the week is acceptable."""


class TestTime(ImplicitDict):
    """Exactly one of the fields of this object must be specified."""

    absolute_time: Optional[StringBasedDateTime] = None
    """Use a precise timestamp which does not change with test conditions.

    The value of absolute_time is limited given that the specific time a test will be started is unknown, and the jurisdictions usually impose a limit on how far in the future an operation can be planned.
    """

    test_time: Optional[dict] = None
    """If specified, use the timestamp at which the current test run started."""

    next_day: Optional[NextDay] = None
    """Use a timestamp equal to midnight beginning the next occurrence of any matching day following the specified reference timestamp."""

    next_sun_position: Optional[NextSunPosition] = None
    """Use a timestamp equal to the next time after the specified reference timestamp at which the sun will be at the specified angle above the horizon.

    Sun angle calculations will be based on a location relevant to the query (e.g., within flight volumes), but are not guaranteed to precisely match any particular location.
    """

    offset_from: Optional[OffsetTime] = None
    """Use a timestamp that is offset by the specified amount from the specified time."""


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
    DayOfTheWeek.M,
    DayOfTheWeek.T,
    DayOfTheWeek.W,
    DayOfTheWeek.Th,
    DayOfTheWeek.F,
    DayOfTheWeek.Sa,
    DayOfTheWeek.Su,
]
"""Days of the week with indices corresponding with datetime.weekdays()"""


def resolve_time(test_time: TestTime, start_of_test: datetime) -> datetime:
    """Resolve TestTime into specific datetime."""
    if test_time.absolute_time is not None:
        return test_time.absolute_time.datetime
    elif test_time.test_time is not None:
        return start_of_test
    elif test_time.next_day is not None:
        t = resolve_time(test_time.next_day.starting_from, start_of_test)
        t = datetime(
            year=t.year, month=t.month, day=t.day, tzinfo=t.tzinfo
        ) + timedelta(days=1)
        if test_time.next_day.days_of_the_week:
            allowed_weekdays = {
                _weekdays.index(d) for d in test_time.next_day.days_of_the_week
            }
            while t.weekday() not in allowed_weekdays:
                t += timedelta(days=1)
        return t
    elif test_time.offset_from is not None:
        return (
            resolve_time(test_time.offset_from.starting_from, start_of_test)
            + test_time.offset_from.offset.timedelta
        )
    elif test_time.next_sun_position is not None:
        # TODO: Implement times based on sun position
        raise NotImplementedError(
            "TestTimes based on sun position are not yet implemented"
        )
    else:
        raise NotImplementedError(
            "TestTime did not specify a supported option for defining a time"
        )


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
