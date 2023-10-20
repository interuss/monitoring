import uuid
from datetime import datetime
from typing import List, Tuple

import arrow
from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.rid.v1.injection import ChangeTestResponse

from monitoring.monitorlib import geo
from monitoring.monitorlib.rid_automated_testing.injection_api import (
    TestFlight,
    CreateTestParameters,
)
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.netrid import (
    FlightDataResource,
    NetRIDServiceProviders,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class InjectedFlight(ImplicitDict):
    uss_participant_id: str
    test_id: str
    flight: TestFlight
    query_timestamp: datetime


class InjectedTest(ImplicitDict):
    participant_id: str
    test_id: str
    version: str


def inject_flights(
    test_scenario: TestScenario,
    flights_data_res: FlightDataResource,
    service_providers_res: NetRIDServiceProviders,
) -> Tuple[List[InjectedFlight], List[InjectedTest]]:
    test_id = str(uuid.uuid4())
    test_flights = flights_data_res.get_test_flights()
    service_providers = service_providers_res.service_providers

    injected_flights: List[InjectedFlight] = []
    injected_tests: List[InjectedTest] = []

    if len(service_providers) > len(test_flights):
        raise ValueError(
            f"{len(service_providers)} service providers were specified, but data for only {len(test_flights)} test flights were provided"
        )
    for i, target in enumerate(service_providers):
        p = CreateTestParameters(requested_flights=[test_flights[i]])
        with test_scenario.check(
            "Successful injection", [target.participant_id]
        ) as check:
            query = target.submit_test(p, test_id)
            test_scenario.record_query(query)

            if query.status_code != 200:
                check.record_failed(
                    summary="Error while trying to inject test flight",
                    severity=Severity.High,
                    details=f"Expected response code 200 from {target.participant_id} but received {query.status_code} while trying to inject a test flight",
                    query_timestamps=[query.request.timestamp],
                )

            if "json" not in query.response or query.response.json is None:
                check.record_failed(
                    summary="Response to test flight injection request did not contain a JSON body",
                    severity=Severity.High,
                    details=f"Expected a JSON body in response to flight injection request",
                    query_timestamps=[query.request.timestamp],
                )

        changed_test: ChangeTestResponse = ImplicitDict.parse(
            query.response.json, ChangeTestResponse
        )
        injected_tests.append(
            InjectedTest(
                participant_id=target.participant_id,
                test_id=test_id,
                version=changed_test.version,
            )
        )

        start_time = None
        end_time = None
        for flight in changed_test.injected_flights:
            injected_flights.append(
                InjectedFlight(
                    uss_participant_id=target.participant_id,
                    test_id=test_id,
                    flight=TestFlight(flight),
                    query_timestamp=query.request.timestamp,
                )
            )
            earliest_time = min(t.timestamp.datetime for t in flight.telemetry)
            latest_time = max(t.timestamp.datetime for t in flight.telemetry)
            if start_time is None or earliest_time < start_time:
                start_time = earliest_time
            if end_time is None or latest_time > end_time:
                end_time = latest_time
        now = arrow.utcnow().datetime
        dt0 = (start_time - now).total_seconds()
        dt1 = (end_time - now).total_seconds()
        test_scenario.record_note(
            f"{test_id} time range",
            f"Injected flights start {dt0:.1f} seconds from now and end {dt1:.1f} seconds from now",
        )

    # Make sure the injected flights can be identified correctly by the test harness
    with test_scenario.check("Identifiable flights") as check:
        errors = injected_flights_errors(injected_flights)
        if errors:
            check.record_failed(
                summary="Injected flights not suitable for test",
                severity=Severity.High,
                details="When checking the suitability of the flights (as injected) for the test, found:\n"
                + "\n".join(errors),
                query_timestamps=[f.query_timestamp for f in injected_flights],
            )

    return injected_flights, injected_tests


def injected_flights_errors(injected_flights: List[InjectedFlight]) -> List[str]:
    """Determine whether each telemetry in each injected flight can be easily distinguished from each other.

    Args:
        injected_flights: Full set of flights injected into Service Providers.

    Returns: List of error messages, or an empty list if no errors.
    """
    errors: List[str] = []
    for f1, injected_flight in enumerate(injected_flights):
        for t1, injected_telemetry in enumerate(injected_flight.flight.telemetry):
            for t2, other_telemetry in enumerate(
                injected_flight.flight.telemetry[t1 + 1 :]
            ):
                if geo.LatLngPoint.from_f3411(injected_telemetry.position).match(
                    geo.LatLngPoint.from_f3411(other_telemetry.position)
                ):
                    errors.append(
                        f"{injected_flight.uss_participant_id}'s flight with injection ID {injected_flight.flight.injection_id} in test {injected_flight.test_id} has telemetry at indices {t1} and {t1 + 1 + t2} which can be mistaken for each other; (lat={injected_telemetry.position.lat}, lng={injected_telemetry.position.lng}) and (lat={other_telemetry.position.lat}, lng={other_telemetry.position.lng}) respectively"
                    )
            for f2, other_flight in enumerate(injected_flights[f1 + 1 :]):
                for t2, other_telemetry in enumerate(other_flight.flight.telemetry):
                    if geo.LatLngPoint.from_f3411(injected_telemetry.position).match(
                        geo.LatLngPoint.from_f3411(other_telemetry.position)
                    ):
                        errors.append(
                            f"{injected_flight.uss_participant_id}'s flight with injection ID {injected_flight.flight.injection_id} in test {injected_flight.test_id} has telemetry at index {t1} that can be mistaken for telemetry index {t2} in {other_flight.uss_participant_id}'s flight with injection ID {other_flight.flight.injection_id} in test {other_flight.test_id}; (lat={injected_telemetry.position.lat}, lng={injected_telemetry.position.lng}) and (lat={other_telemetry.position.lat}, lng={other_telemetry.position.lng}) respectively"
                        )
    return errors
