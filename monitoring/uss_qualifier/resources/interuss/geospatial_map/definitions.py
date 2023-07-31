from __future__ import annotations
from enum import Enum
from typing import List, Optional

from implicitdict import ImplicitDict, StringBasedTimeDelta, StringBasedDateTime
from monitoring.monitorlib.scd import Circle, Altitude, Polygon


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


class ExpectedFeatureCheckResult(str, Enum):
    Block = "Block"
    """When a service provider being tested as a geo-awareness map provider is queried for whether any features are present for the specified volumes that would cause the flight described in this feature check to be blocked, the service provider must respond affirmatively; responding negatively will cause a failed check."""

    Advise = "Advise"
    """When a service provider being tested as a geo-awareness map provider is queried for whether any features are present for the specified volumes that would provide an advisory to the viewer viewing a map relevant to the planning of the flight described in this feature check, the service provider must respond affirmatively; responding negatively will cause a failed check.  The service provider does not need to include the content or number of advisories in its response."""

    Neither = "Neither"
    """When a service provider being tested as a geo-awareness map provider is queried for whether any features matching the other criteria in this feature check and causing a “block” or “advise” per above are present with the specified criteria, the service provider must respond negatively; responding affirmatively will cause a failed check."""


class FeatureCheck(ImplicitDict):
    geospatial_check_id: str
    """Unique (within table) test step/row identifier."""

    requirement_ids: List[str]
    """Jurisdictional identifiers of the requirements this test step is evaluating."""

    description: str
    """Human-readable test step description to aid in the debugging and traceability."""

    operation_rule_set: Optional[str] = None
    """The set of operating rules (or rule set) under which the operation described in the feature check should be performed."""

    volumes: List[Volume4DTemplate]
    """Spatial and temporal definition of the areas the virtual user intends to fly in.

    A service provider is expected to provide geospatial features relevant to any of the entire area specified and for any of the entire time specified.
    """

    restriction_source: Optional[str] = None
    """Which source for geospatial features describing restrictions should be considered when looking for the expected outcome."""

    expected_result: ExpectedFeatureCheckResult
    """Expected outcome when checking map for features as described."""


class FeatureCheckTable(ImplicitDict):
    rows: List[FeatureCheck]
