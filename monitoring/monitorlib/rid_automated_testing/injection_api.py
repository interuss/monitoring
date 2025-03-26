import datetime
from typing import List, Optional, Tuple

import arrow
import s2sphere
from uas_standards.interuss.automated_testing.rid.v1 import injection
from uas_standards.interuss.automated_testing.rid.v1.injection import (
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

    raw_telemetry: Optional[List[RIDAircraftState]]
    """Copy of original telemetry with potential invalid data"""

    def __init__(self, *args, **kwargs):
        """Build a new test flight instance

        Args:
            filter_invalid_telemetry: If enabled, the constructor will filter out any invalid telemetry data. A copy of initial data is kept in the raw_telemetry field. Default to true.
            Any other argument is passed to the parent injection.TestFlight class.
        """

        super().__init__(*args, **kwargs)

        # We filter out bad telemetry but keep a copy in raw_telemetry
        self.raw_telemetry = self.telemetry

        filter_invalid_telemetry = kwargs.pop("filter_invalid_telemetry", True)

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
                    if telemetry.position.get(mandatory_field, None) is None:
                        is_ok = False
                        break

                if not is_ok:
                    continue

                filtered_telemetry.append(telemetry)

            self.telemetry = filtered_telemetry

    def get_span(
        self,
    ) -> Tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
        earliest = None
        latest = None
        times = [
            arrow.get(aircraft_state.timestamp).datetime
            for aircraft_state in self.telemetry
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

    def get_details(self, t_now: datetime.datetime) -> Optional[RIDFlightDetails]:
        latest_after: Optional[datetime.datetime] = None
        tf_details = None
        for response in self.details_responses:
            t_response = arrow.get(response.effective_after).datetime
            if t_now >= t_response:
                if latest_after is None or t_response > latest_after:
                    latest_after = t_response
                    tf_details = response.details
        return tf_details

    def get_id(self, t_now: datetime.datetime) -> Optional[str]:
        details = self.get_details(t_now)
        return details.id if details else None

    def get_aircraft_type(self, rid_version: RIDVersion) -> UAType:
        if not self.has_field_with_value("aircraft_type"):
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
            self.telemetry, key=lambda telemetry: telemetry.timestamp.datetime
        )

    def select_relevant_states(
        self, view: s2sphere.LatLngRect, t0: datetime.datetime, t1: datetime.datetime
    ) -> List[RIDAircraftState]:
        recent_states: List[RIDAircraftState] = []
        previously_outside = False
        previously_inside = False
        previous_telemetry = None
        for telemetry in self.telemetry:
            if telemetry.timestamp.datetime < t0 or telemetry.timestamp.datetime > t1:
                # Telemetry not relevant based on time
                continue
            pt = s2sphere.LatLng.from_degrees(
                telemetry.position.lat, telemetry.position.lng
            )
            inside_now = view.contains(pt)
            if inside_now:
                if previously_outside:
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

    def get_rect(self) -> Optional[s2sphere.LatLngRect]:
        return geo.bounding_rect(
            [(t.position.lat, t.position.lng) for t in self.telemetry]
        )

    def get_mean_update_rate_hz(self) -> Optional[float]:
        """
        Calculate the mean update rate of the telemetry in Hz
        """
        if not self.telemetry or len(self.telemetry) == 1:
            return None
        # TODO check if required or not (may have been called earlier?)
        self.order_telemetry()
        start = self.telemetry[0].timestamp.datetime
        end = self.telemetry[-1].timestamp.datetime
        return (len(self.telemetry) - 1) / (end - start).seconds


class CreateTestParameters(injection.CreateTestParameters):
    def get_span(
        self,
    ) -> Tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
        if not self.requested_flights:
            return (None, None)
        (earliest, latest) = (None, None)
        for flight in self.requested_flights:
            flight = TestFlight(flight)
            (t0, t1) = flight.get_span()
            if earliest is None or t0 < earliest:
                earliest = t0
            if latest is None or t1 > latest:
                latest = t1
        return (earliest, latest)

    def get_rect(self) -> Optional[s2sphere.LatLngRect]:
        result = None
        for flight in self.requested_flights:
            flight = TestFlight(flight)
            if result is None:
                result = flight.get_rect()
            else:
                result = result.union(flight.get_rect())
        return result
