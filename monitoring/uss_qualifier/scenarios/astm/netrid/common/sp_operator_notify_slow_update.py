import datetime

import arrow
from future.backports.datetime import timedelta
from requests.exceptions import RequestException
from s2sphere import LatLngRect

from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.netrid import (
    EvaluationConfigurationResource,
    FlightDataResource,
    NetRIDServiceProviders,
)
from monitoring.uss_qualifier.resources.netrid.service_providers import (
    NetRIDServiceProvider,
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


class ServiceProviderNotifiesSlowUpdates(GenericTestScenario):
    _flights_data: FlightDataResource
    _service_providers: NetRIDServiceProviders
    _evaluation_configuration: EvaluationConfigurationResource

    _injected_flights: list[InjectedFlight]
    _injected_tests: list[InjectedTest]

    _pre_injection_notifications: dict[str, list[str]] = {}
    _notifications_before: datetime
    _notifications_after: datetime

    _unobserved_notifications: list[NetRIDServiceProvider]

    def __init__(
        self,
        flights_data: FlightDataResource,
        service_providers: NetRIDServiceProviders,
        evaluation_configuration: EvaluationConfigurationResource,
    ):
        super().__init__()

        self._flights_data = flights_data.drop_every_n_state(2).freeze_flights()
        self._service_providers = service_providers
        self._evaluation_configuration = evaluation_configuration
        self._injected_tests = []

        # default bounds if test flights have no data (in which case the scenario won't work anyway)
        after = arrow.utcnow().datetime
        before = arrow.utcnow().datetime + timedelta(hours=1)
        for tf in self._flights_data.get_test_flights():
            start, end = tf.get_span()
            after = min(after, start)
            before = max(before, end)

        self._notifications_after = after
        self._notifications_before = before

    @property
    def _rid_version(self) -> RIDVersion:
        raise NotImplementedError(
            "ServiceProviderNotifiesSlowUpdates test scenario subclass must specify _rid_version"
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        for flight in self._flights_data.flight_collection.flights:
            duration = (
                flight.states[-1].timestamp.datetime
                - flight.states[0].timestamp.datetime
            )
            if duration.seconds < 61:
                self.record_note(
                    "flight_duration",
                    f"Flight {flight.flight_details.id} is relatively short ({duration.seconds} seconds), "
                    f"must be at least 61 seconds to match scenario expectations: this flight might cause the "
                    f"scenario to fail depending on how Service Providers diagnose a too slow telemetry rate.",
                )

        self.begin_test_case("Slow updates flight")

        self.begin_test_step("Establish notification baseline")
        self._step_check_current_notifs()
        self.end_test_step()

        self.begin_test_step("Injection")
        self._inject_flights()
        self.end_test_step()

        self._poll_during_flights()

        self.begin_test_step("Verify operator notification")
        self._step_verify_operator_notification()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _step_check_current_notifs(self):
        self._pre_injection_notifications = injection.get_user_notifications(
            self,
            self._service_providers,
            after=self._notifications_after,
            before=self._notifications_before,
        )

    def _inject_flights(self):
        (self._injected_flights, self._injected_tests) = injection.inject_flights(
            self, self._flights_data, self._service_providers
        )

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
            test_scenario=self,
            service_providers=self._service_providers,
            config=config,
            rid_version=self._rid_version,
            initial_notifications=self._pre_injection_notifications,
            notification_before=self._notifications_before,
            notification_after=self._notifications_after,
        )

        def poll_fct(rect: LatLngRect) -> bool:
            return evaluator.evaluate_new_notifications(rect)

        virtual_observer.start_polling(
            config.min_polling_interval.timedelta,
            [
                self._rid_version.max_details_diagonal_km * 1000 - 100,  # details
            ],
            poll_fct,
        )

        self._unobserved_notifications = evaluator.remaining_notifications_to_observe()

    def _step_verify_operator_notification(self):
        no_notif_participants = [
            sp.participant_id for sp in self._unobserved_notifications
        ]
        for sp in self._service_providers.service_providers:
            with self.check(
                "Operator notification present",
                sp.participant_id,
            ) as check:
                if sp.participant_id in no_notif_participants:
                    check.record_failed(
                        summary="No operator notification found",
                        details="No operator notification was found when at least one would have been expected due to the too low update rate of the injected telemetry.",
                    )

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
