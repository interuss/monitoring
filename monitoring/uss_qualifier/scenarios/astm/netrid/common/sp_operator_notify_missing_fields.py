import arrow
from requests.exceptions import RequestException
from s2sphere import LatLngRect

from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.rid_automated_testing.injection_api import (
    MANDATORY_POSITION_FIELDS,
    MANDATORY_TELEMETRY_FIELDS,
)
from monitoring.uss_qualifier.resources.netrid import (
    EvaluationConfigurationResource,
    FlightDataResource,
    NetRIDServiceProviders,
)
from monitoring.uss_qualifier.scenarios.astm.netrid import (
    display_data_evaluator,
    injection,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.injected_flight_collection import (
    InjectedFlightCollection,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.injection import (
    InjectedFlight,
    InjectedTest,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.virtual_observer import (
    VirtualObserver,
)
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class SpOperatorNotifyMissingFields(GenericTestScenario):
    _flights_data: FlightDataResource
    _service_providers: NetRIDServiceProviders
    _evaluation_configuration: EvaluationConfigurationResource

    _injected_flights: list[InjectedFlight]
    _injected_tests: list[InjectedTest]

    def __init__(
        self,
        flights_data: FlightDataResource,
        service_providers: NetRIDServiceProviders,
        evaluation_configuration: EvaluationConfigurationResource,
    ):
        super().__init__()
        self._flights_data = flights_data
        self._service_providers = service_providers
        self._evaluation_configuration = evaluation_configuration
        self._injected_tests = []

    @property
    def _rid_version(self) -> RIDVersion:
        raise NotImplementedError(
            "SpOperatorNotifyMissingFields test scenario subclass must specify _rid_version"
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Missing fields flight")

        for field in MANDATORY_TELEMETRY_FIELDS + [
            f"position.{f}" for f in MANDATORY_POSITION_FIELDS
        ]:
            if field == "timestamp":
                # TODO: See #1042: Telemetry may be used as timing for data
                # delivery, blanking it may confuse USSs
                continue

            self._frozen_flights_data = self._flights_data.truncate_flights_field(
                field
            ).freeze_flights()
            start_time, end_time = self._compute_notification_boundaries(
                self._frozen_flights_data
            )
            self._notifications_before = end_time
            self._notifications_after = start_time

            self.begin_test_step("Retrieve pre-existing operator notification")
            self._retrieve_notifications()
            self.end_test_step()

            self.begin_test_step("Injection")
            self._inject_flights()
            self.end_test_step()

            self._poll_during_flights()

        self.end_test_case()
        self.end_test_scenario()

    def _compute_notification_boundaries(self, flights_data):
        start_time = arrow.utcnow()
        end_time = arrow.utcnow()

        for flight in flights_data.get_test_flights():
            for telemetry in flight.telemetry:
                timestamp = telemetry.get("timestamp", None)
                if timestamp:
                    start_time = min(start_time, timestamp.datetime)
                    end_time = max(end_time, timestamp.datetime)

        return start_time, end_time

    def _retrieve_notifications(self):
        self._pre_injection_notifications = injection.get_user_notifications(
            self,
            self._service_providers,
            before=self._notifications_before,
            after=self._notifications_after,
        )

    def _inject_flights(self):
        self._injected_flights, new_injected_tests = injection.inject_flights(
            self, self._frozen_flights_data, self._service_providers
        )

        self._injected_tests += new_injected_tests

    def _poll_during_flights(self):
        config = self._evaluation_configuration.configuration

        virtual_observer = VirtualObserver(
            injected_flights=InjectedFlightCollection(self._injected_flights),
            repeat_query_rect_period=config.repeat_query_rect_period,
            min_query_diagonal_m=config.min_query_diagonal,
            relevant_past_data_period=self._rid_version.realtime_period
            + config.max_propagation_latency.timedelta,
        )
        evaluator = display_data_evaluator.NotificationsEvaluator(
            self,
            self._service_providers,
            config,
            self._rid_version,
            self._pre_injection_notifications,
            self._notifications_before,
            self._notifications_after,
        )

        def poll_fct(rect: LatLngRect) -> bool:
            return evaluator.evaluate_new_notifications(rect)

        virtual_observer.start_polling(
            config.min_polling_interval.timedelta,
            [
                self._rid_version.max_diagonal_km * 1000 - 100,  # clustered
                self._rid_version.max_details_diagonal_km * 1000 - 100,  # details
            ],
            poll_fct,
        )

        self.begin_test_step("Verify operator notification")
        unobserved_notifications = evaluator.remaining_notifications_to_observe()

        for service_provider in self._service_providers.service_providers:
            with self.check(
                "All injected flights have generated user notifications",
                [service_provider.participant_id],
            ) as check:
                if service_provider in unobserved_notifications:
                    check.record_failed(
                        summary="Some notifications were not observed",
                        details=f"The following service provider didn't generated notifications even when flights data had missing field injected: {service_provider}",
                    )
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        while self._injected_tests:
            injected_test = self._injected_tests.pop()
            matching_sps = [
                sp
                for sp in self._service_providers.service_providers
                if sp.participant_id == injected_test.participant_id
            ]
            if len(matching_sps) != 1:
                matching_ids = ", ".join(sp.participant_id for sp in matching_sps)
                raise RuntimeError(
                    f"Found {len(matching_sps)} service providers with participant ID {injected_test.participant_id} ({matching_ids}) when exactly 1 was expected"
                )
            sp = matching_sps[0]
            check = self.check("Successful test deletion", [sp.participant_id])
            try:
                query = sp.delete_test(injected_test.test_id, injected_test.version)
                self.record_query(query)
                if query.status_code != 200:
                    raise ValueError(
                        f"Received status code {query.status_code} after attempting to delete test {injected_test.test_id} at version {injected_test.version} from service provider {sp.participant_id}"
                    )
                check.record_passed()
            except (RequestException, ValueError) as e:
                stacktrace = stacktrace_string(e)
                check.record_failed(
                    summary="Error while trying to delete test flight",
                    details=f"While trying to delete a test flight from {sp.participant_id}, encountered error:\n{stacktrace}",
                )
        self.end_cleanup()
