import datetime
from collections import defaultdict

import arrow
import s2sphere
from implicitdict import Optional
from uas_standards.interuss.automated_testing.rid.v1 import injection
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    UASID,
    RIDAircraftState,
    RIDFlightDetails,
    UAType,
)

from monitoring.monitorlib import geo
from monitoring.monitorlib.rid import RIDVersion

SCOPE_RID_QUALIFIER_INJECT = "rid.inject_test_data"

MANDATORY_TELEMETRY_FIELDS = [
    "timestamp",
    "timestamp_accuracy",
    "position",
    "track",
    "speed",
    "speed_accuracy",
    "vertical_speed",
]

# TODO: Handle accuracy_h and accuracy_v
MANDATORY_POSITION_FIELDS = ["lat", "lng", "alt"]


class TestFlight(injection.TestFlight):
    raw_telemetry: Optional[list[RIDAircraftState]]
    """Copy of original telemetry with potential invalid data"""

    def __init__(self, *args, **kwargs):
        """Build a new test flight instance

        Args:
            filter_invalid_telemetry: If enabled, the constructor will filter out any invalid telemetry data. A copy of initial data is kept in the raw_telemetry field. Default to true.
            Any other argument is passed to the parent injection.TestFlight class.
        """

        filter_invalid_telemetry = kwargs.pop("filter_invalid_telemetry", True)

        super().__init__(*args, **kwargs)

        # We filter out bad telemetry but keep a copy in raw_telemetry
        self.raw_telemetry = self.telemetry

        if filter_invalid_telemetry:
            filtered_telemetry = []

            for telemetry in self.telemetry:
                is_ok = True

                for mandatory_field in MANDATORY_TELEMETRY_FIELDS:
                    if telemetry.get(mandatory_field, None) is None:
                        is_ok = False
                        break

                if not is_ok:
                    continue

                for mandatory_field in MANDATORY_POSITION_FIELDS:
                    if (
                        not telemetry.position
                        or telemetry.position.get(mandatory_field, None) is None
                    ):
                        is_ok = False
                        break

                if not is_ok:
                    continue

                filtered_telemetry.append(telemetry)

            self.telemetry = filtered_telemetry

        # Right now, injection API specfic two method of injecting the
        # serial_number and registration_number.
        # To ensure consistency, we do inject both if one value is present,
        # raise an expcetion if we do have different value and do nothing
        # if none are present

        for detail in self.details_responses:
            # Values outside uas_id
            serial_number = detail.details.get("serial_number")
            registration_number = detail.details.get("registration_number")

            # No uas_id and one value present: We build a uas_id that we will
            # fill at next step
            if ("uas_id" not in detail.details or not detail.details.uas_id) and (
                serial_number or registration_number
            ):
                detail.details.uas_id = UASID()

            if detail.details.uas_id is not None:
                if detail.details.uas_id.serial_number:
                    if not serial_number:  # No serial number outside uas_id, we set it
                        detail.details.serial_number = (
                            detail.details.uas_id.serial_number
                        )
                    elif serial_number != detail.details.uas_id.serial_number:
                        raise ValueError(
                            f"Impossible to validate test flight: details.serial_number ({serial_number}) is not equal to details.uas_id.serial_number ({detail.details.uas_id.serial_number})"
                        )
                elif serial_number:  # No serial_number is uas_id, but we do have one externally: we do set it in uas_id
                    detail.details.uas_id.serial_number = serial_number

                if detail.details.uas_id.registration_id:
                    if (
                        not registration_number
                    ):  # No serial number outside uas_id, we set it
                        detail.details.registration_number = (
                            detail.details.uas_id.registration_id
                        )
                    elif registration_number != detail.details.uas_id.registration_id:
                        raise ValueError(
                            f"Impossible to validate test flight: details.registration_number ({registration_number}) is not eqal to details.uas_id.registration_id ({detail.details.uas_id.registration_id})"
                        )
                elif registration_number:  # No serial_number is uas_id, but we do have one externally: we do set it in uas_id
                    detail.details.uas_id.registration_id = registration_number

    def get_span(
        self,
    ) -> tuple[datetime.datetime | None, datetime.datetime | None]:
        earliest = None
        latest = None
        times = [
            arrow.get(aircraft_state.timestamp).datetime
            for aircraft_state in self.telemetry
            if aircraft_state.timestamp
        ]
        times.extend(
            arrow.get(details.effective_after).datetime
            for details in self.details_responses
        )
        for t in times:
            if earliest is None or t < earliest:
                earliest = t
            if latest is None or t > latest:
                latest = t
        return (earliest, latest)

    def get_details(self, t_now: datetime.datetime) -> RIDFlightDetails | None:
        latest_after: datetime.datetime | None = None
        tf_details = None
        for response in self.details_responses:
            t_response = arrow.get(response.effective_after).datetime
            if t_now >= t_response:
                if latest_after is None or t_response > latest_after:
                    latest_after = t_response
                    tf_details = response.details
        return tf_details

    def get_id(self, t_now: datetime.datetime) -> str | None:
        details = self.get_details(t_now)
        return details.id if details else None

    def get_aircraft_type(self, rid_version: RIDVersion) -> UAType:
        if not self.has_field_with_value("aircraft_type") or not self.aircraft_type:
            return UAType.NotDeclared

        # there exists a small difference in the enums between both versions of RID, this ensures we always return the expected one
        if (
            rid_version == RIDVersion.f3411_19
            and self.aircraft_type == UAType.HybridLift
        ):
            return UAType.VTOL
        if rid_version == RIDVersion.f3411_22a and self.aircraft_type == UAType.VTOL:
            return UAType.HybridLift

        return self.aircraft_type

    def order_telemetry(self):
        self.telemetry = sorted(
            self.telemetry,
            key=lambda telemetry: telemetry.timestamp.datetime
            if telemetry.timestamp
            else 0,
        )

    def select_relevant_states(
        self, view: s2sphere.LatLngRect, t0: datetime.datetime, t1: datetime.datetime
    ) -> list[RIDAircraftState]:
        recent_states: list[RIDAircraftState] = []
        previously_outside = False
        previously_inside = False
        previous_telemetry = None
        for telemetry in self.telemetry:
            if (
                not telemetry.timestamp
                or telemetry.timestamp.datetime < t0
                or telemetry.timestamp.datetime > t1
            ):
                # Telemetry not relevant based on time
                continue
            if not telemetry.position:
                continue
            pt = s2sphere.LatLng.from_degrees(
                telemetry.position.lat, telemetry.position.lng
            )
            inside_now = view.contains(pt)
            if inside_now:
                if previously_outside and previous_telemetry:
                    recent_states.append(previous_telemetry)
                recent_states.append(telemetry)
                previously_inside = True
                previously_outside = False
            else:
                if previously_inside:
                    recent_states.append(telemetry)
                previously_outside = True
                previously_inside = False
            previous_telemetry = telemetry
        return recent_states

    def get_rect(self) -> s2sphere.LatLngRect | None:
        return geo.bounding_rect(
            [
                (t.position.lat, t.position.lng)
                for t in self.telemetry
                if t.position and t.position.lat and t.position.lng
            ]
        )

    def get_update_rates(self) -> list[int] | None:
        """Return the update rate for every second, relative to the start of the flight, with a moving windows of 3 seconds."""

        if not self.telemetry or len(self.telemetry) == 1:
            return None
        # TODO check if required or not (may have been called earlier?)
        self.order_telemetry()

        if not self.telemetry[0].timestamp or not self.telemetry[-1].timestamp:
            return
        start = self.telemetry[0].timestamp.datetime
        end = self.telemetry[-1].timestamp.datetime

        buckets = defaultdict(int)

        for frame in self.telemetry:
            if frame.timestamp is not None:
                bucket = int((frame.timestamp.datetime - start).total_seconds())
                buckets[bucket] += 1

        rates = []

        last_bucket = int((end - start).total_seconds())
        bucket = 2

        while bucket <= last_bucket:
            rates.append(
                (buckets[bucket] + buckets[bucket - 1] + buckets[bucket - 2]) / 3.0
            )
            bucket += 1

        return rates


class CreateTestParameters(injection.CreateTestParameters):
    def get_span(
        self,
    ) -> tuple[datetime.datetime | None, datetime.datetime | None]:
        if not self.requested_flights:
            return (None, None)
        (earliest, latest) = (None, None)
        for flight in self.requested_flights:
            flight = TestFlight(flight)
            (t0, t1) = flight.get_span()
            if t0 and (earliest is None or t0 < earliest):
                earliest = t0
            if t1 and (latest is None or t1 > latest):
                latest = t1
        return (earliest, latest)

    def get_rect(self) -> s2sphere.LatLngRect | None:
        result = None
        for flight in self.requested_flights:
            flight = TestFlight(flight)
            if result is None:
                result = flight.get_rect()
            else:
                result = result.union(flight.get_rect())
        return result
