import copy
import json
import uuid
from datetime import timedelta
from typing import List, Optional, Self

import arrow
from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.astm.f3411.v22a.api import UASID
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    RIDAircraftState,
    TestFlightDetails,
)

from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.rid_automated_testing.injection_api import TestFlight
from monitoring.uss_qualifier.resources.files import load_content, load_dict
from monitoring.uss_qualifier.resources.netrid.flight_data import (
    FlightDataSpecification,
    FlightRecordCollection,
)
from monitoring.uss_qualifier.resources.netrid.simulation.adjacent_circular_flights_simulator import (
    generate_aircraft_states,
)
from monitoring.uss_qualifier.resources.netrid.simulation.kml_flights import (
    get_flight_records,
)
from monitoring.uss_qualifier.resources.resource import Resource


class FlightDataResource(Resource[FlightDataSpecification]):
    _flight_start_delay: timedelta
    flight_collection: FlightRecordCollection

    # If set, this field will be removed from the first telemetry frame
    _field_to_clean = None

    def __init__(self, specification: FlightDataSpecification, resource_origin: str):
        super(FlightDataResource, self).__init__(specification, resource_origin)
        if "record_source" in specification:
            self.flight_collection = ImplicitDict.parse(
                load_dict(specification.record_source),
                FlightRecordCollection,
            )
        elif "adjacent_circular_flights_simulation_source" in specification:
            self.flight_collection = generate_aircraft_states(
                specification.adjacent_circular_flights_simulation_source
            )
        elif "kml_source" in specification:
            kml_content = load_content(specification.kml_source.kml_file)
            self.flight_collection = get_flight_records(
                kml_content,
                specification.kml_source.reference_time.datetime,
                specification.kml_source.random_seed,
            )
        else:
            raise ValueError(
                "A source of flight data was not identified in the specification for a FlightDataSpecification:\n"
                + json.dumps(specification, indent=2)
            )
        self._flight_start_delay = specification.flight_start_delay.timedelta

    def get_test_flights(
        self, rid_version: Optional[RIDVersion] = None
    ) -> List[TestFlight]:
        t0 = arrow.utcnow() + self._flight_start_delay

        test_flights: List[TestFlight] = []

        for flight in self.flight_collection.flights:
            dt = t0 - flight.reference_time.datetime

            telemetry: List[RIDAircraftState] = []

            removed_field = False

            for state in flight.states:
                shifted_state = RIDAircraftState(state)
                shifted_state.timestamp = StringBasedDateTime(
                    state.timestamp.datetime + dt
                )

                if not removed_field and self._field_to_clean:
                    shifted_state = copy.deepcopy(shifted_state)

                    if self._field_to_clean.startswith("position."):
                        target = shifted_state["position"]
                        field_to_clean = self._field_to_clean[len("position.") :]
                    else:
                        target = shifted_state
                        field_to_clean = self._field_to_clean

                    if getattr(target, field_to_clean, None) is not None:
                        setattr(target, field_to_clean, None)
                        removed_field = True  # We only remove data in one frame, stop further removal

                telemetry.append(shifted_state)

            details = TestFlightDetails(
                effective_after=StringBasedDateTime(t0),
                details=flight.flight_details,
            )

            if (
                rid_version == RIDVersion.f3411_22a
            ):  # If not present, we do inject the v22 version of id
                if "uas_id" not in details.details:

                    utm_id = str(
                        uuid.UUID(
                            int=(2**128 - uuid.UUID(details.details.id).int), version=4
                        )
                    )

                    details.details["uas_id"] = UASID(
                        serial_number=details.details.get("serial_number"),
                        registration_id=details.details.get("registration_number"),
                        utm_id=str(utm_id),
                        specific_session_id=f"02-{utm_id.replace('-', '')[:19]}",
                    )

            test_flights.append(
                TestFlight(
                    injection_id=str(uuid.uuid4()),
                    telemetry=telemetry,
                    details_responses=[details],
                    aircraft_type=flight.aircraft_type,
                    filter_invalid_telemetry=not bool(
                        self._field_to_clean
                    ),  # If we wanted to remove a field, disable telemetry data validation
                )
            )

        return test_flights

    def truncate_flights_duration(self, duration: timedelta) -> Self:
        """
        Ensures that the injected flight data will only contain telemetry for at most the specified duration.

        Returns a new, updated instance. The original instance remains unchanged.

        Intended to be used for simulating the disconnection of a networked UAS.
        """
        self_copy = copy.deepcopy(self)
        for flight in self_copy.flight_collection.flights:
            latest_allowed_end = flight.reference_time.datetime + duration
            # Keep only the states within the allowed duration
            flight.states = [
                state
                for state in flight.states
                if state.timestamp.datetime <= latest_allowed_end
            ]
        return self_copy

    def truncate_flights_field(self, field_name: str) -> Self:
        """
        Ensures that the injected flight data are missing telemetric data for the field specified.

        Only the first telemetry with a valid data for the field is edited.

        Returns a new, updated instance. The original instance remains unchanged.

        Intended to be used for simulating missing field scenario.
        """
        self_copy = copy.deepcopy(self)
        self_copy._field_to_clean = field_name  # Cleanup is done in get_test_flights

        return self_copy

    def freeze_flights(self) -> Self:
        """
        Ensures that the injected flight data are generated now and won't be changed in the futur.

        Returns a new, updated instance. The original instance remains unchanged.

        Intended to be used for having the boundaries of the flight's span available before injection.
        """
        self_copy = copy.deepcopy(self)

        flights = self_copy.get_test_flights()

        def new_test_flights(self, rid_version=None):
            return flights

        self_copy.get_test_flights = new_test_flights.__get__(
            self_copy, FlightDataResource
        )

        return self_copy

    def drop_every_n_state(self, n: int) -> Self:
        """
        Drops every n-th state from each flight in the collection.

        Returns a new, updated instance. The original instance remains unchanged.

        Intended to be used for simulating slow updates from a networked UAS.
        """
        self_copy = copy.deepcopy(self)
        for flight in self_copy.flight_collection.flights:
            flight.states = flight.states[::n]
        return self_copy


class FlightDataStorageSpecification(ImplicitDict):
    flight_record_collection_path: Optional[str]
    """Path, usually ending with .json, at which to store the FlightRecordCollection"""

    geojson_tracks_path: Optional[str]
    """Path (folder) in which to store track_XX.geojson files, 1 for each flight"""


class FlightDataStorageResource(Resource[FlightDataStorageSpecification]):
    storage_configuration: FlightDataStorageSpecification

    def __init__(
        self, specification: FlightDataStorageSpecification, resource_origin: str
    ):
        super(FlightDataStorageResource, self).__init__(specification, resource_origin)
        self.storage_configuration = specification
