from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict

import arrow
from implicitdict import ImplicitDict, StringBasedTimeDelta, StringBasedDateTime
from pvlib.solarposition import get_solarposition
from uas_standards.astm.f3548.v21 import api as f3548v21

from monitoring.monitorlib.geo import LatLngPoint


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


class TimeDuringTest(str, Enum):
    StartOfTestRun = "StartOfTestRun"
    """The time at which the test run started."""

    StartOfScenario = "StartOfScenario"
    """The time at which the current scenario started."""

    TimeOfEvaluation = "TimeOfEvaluation"
    """The time at which a TestTime was resolved to an absolute time; generally close to 'now'."""


class TestTime(ImplicitDict):
    """Exactly one of the time option fields of this object must be specified."""

    absolute_time: Optional[StringBasedDateTime] = None
    """Time option field to use a precise timestamp which does not change with test conditions.

    The value of absolute_time is limited given that the specific time a test will be started is unknown, and the jurisdictions usually impose a limit on how far in the future an operation can be planned.
    """

    time_during_test: Optional[TimeDuringTest] = None
    """Time option field to, if specified, use a timestamp relating to the current test run."""

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

    def resolve(self, times: Dict[TimeDuringTest, Time]) -> Time:
        """Resolve TestTime into specific Time."""
        result = None
        if self.absolute_time is not None:
            result = self.absolute_time.datetime
        elif self.time_during_test is not None:
            if self.time_during_test not in times:
                raise ValueError(
                    f"Specified {self.time_during_test} time during test was not provided when resolving TestTime"
                )
            result = times[self.time_during_test].datetime
        elif self.next_day is not None:
            t0 = (
                arrow.get(self.next_day.starting_from.resolve(times).datetime)
                .to(self.next_day.time_zone)
                .datetime
            )
            t = datetime(
                year=t0.year, month=t0.month, day=t0.day, tzinfo=t0.tzinfo
            ) + timedelta(days=1)
            if self.next_day.days_of_the_week:
                allowed_weekdays = {
                    _weekdays.index(d) for d in self.next_day.days_of_the_week
                }
                while t.weekday() not in allowed_weekdays:
                    t += timedelta(days=1)
            result = t
        elif self.offset_from is not None:
            result = (
                self.offset_from.starting_from.resolve(times).datetime
                + self.offset_from.offset.timedelta
            )
        elif self.next_sun_position is not None:
            t0 = self.next_sun_position.starting_from.resolve(times).datetime

            dt = timedelta(minutes=5)
            lat = self.next_sun_position.observed_from.lat
            lng = self.next_sun_position.observed_from.lng
            el_target = self.next_sun_position.elevation_deg

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

        if self.use_timezone:
            result = arrow.get(result).to(self.use_timezone).datetime

        return Time(result)


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
