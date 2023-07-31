from datetime import datetime, timedelta

from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.monitorlib.scd import Volume4D, Volume3D
from monitoring.uss_qualifier.resources.interuss.geospatial_map.definitions import (
    FeatureCheckTable,
    Volume4DTemplate,
    TestTime,
    DayOfTheWeek,
)
from monitoring.uss_qualifier.resources.resource import Resource


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


class FeatureCheckTableSpecification(ImplicitDict):
    table: FeatureCheckTable


class FeatureCheckTableResource(Resource):
    table: FeatureCheckTable

    def __init__(self, specification: FeatureCheckTableSpecification):
        self.table = specification.table


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
