from datetime import timedelta
from typing import List, Optional, Type

from future.backports.datetime import datetime
from implicitdict import ImplicitDict
from loguru import logger
from requests.exceptions import RequestException
from s2sphere import LatLngRect
from uas_standards.astm.f3411.v19 import api as api_v19
from uas_standards.astm.f3411.v22a import api as api_v22a

from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.temporal import Time
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstancesResource
from monitoring.uss_qualifier.resources.interuss import IDGeneratorResource
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSResource,
    MockUSSClient,
)
from monitoring.uss_qualifier.resources.netrid import (
    FlightDataResource,
    NetRIDServiceProviders,
    NetRIDObserversResource,
    EvaluationConfigurationResource,
)
from monitoring.uss_qualifier.scenarios.astm.netrid import (
    display_data_evaluator,
    injection,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
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


class NominalBehavior(GenericTestScenario):
    SUB_TYPE = register_resource_type(399, "Subscription")

    _flights_data: FlightDataResource
    _service_providers: NetRIDServiceProviders
    _observers: NetRIDObserversResource
    _mock_uss: MockUSSClient
    _evaluation_configuration: EvaluationConfigurationResource

    _injected_flights: List[InjectedFlight]
    _injected_tests: List[InjectedTest]

    _dss_wrapper: DSSWrapper
    _subscription_id: str

    def __init__(
        self,
        flights_data: FlightDataResource,
        service_providers: NetRIDServiceProviders,
        observers: NetRIDObserversResource,
        mock_uss: Optional[MockUSSResource],
        evaluation_configuration: EvaluationConfigurationResource,
        id_generator: IDGeneratorResource,
        dss_pool: DSSInstancesResource,
    ):
        super().__init__()
        self._flights_data = flights_data
        self._service_providers = service_providers
        self._observers = observers
        self._mock_uss = mock_uss.mock_uss
        self._evaluation_configuration = evaluation_configuration
        self._dss_pool = dss_pool
        self._dss_wrapper = DSSWrapper(self, dss_pool.dss_instances[0])
        self._injected_tests = []

        self._subscription_id = id_generator.id_factory.make_id(self.SUB_TYPE)

    @property
    def _rid_version(self) -> RIDVersion:
        raise NotImplementedError(
            "NominalBehavior test scenario subclass must specify _rid_version"
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")

        if not self._mock_uss:
            self.record_note(
                "notification_testing",
                "Mock USS not available, will skip checks related to notifications",
            )

        self.begin_test_step("Clean workspace")
        # Test flights are being taken care of by preparation step before this scenario
        self._dss_wrapper.cleanup_sub(self._subscription_id)

        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Nominal flight")

        if self._mock_uss:
            self.begin_test_step("Mock USS Subscription")
            self._subscribe_mock_uss()
            self.end_test_step()

        self.begin_test_step("Injection")
        self._inject_flights()
        self.end_test_step()

        self._poll_during_flights()

        if self._mock_uss:
            self.begin_test_step("Validate Mock USS received notification")
            self._validate_mock_uss_notifications(context.start_time)
            self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _subscribe_mock_uss(self):
        dss_wrapper = DSSWrapper(self, self._dss_pool.dss_instances[0])
        # Get all bounding rects for flights
        flight_rects = [f.get_rect() for f in self._flights_data.get_test_flights()]
        flight_union: Optional[LatLngRect] = None
        for fr in flight_rects:
            if flight_union is None:
                flight_union = fr
            else:
                flight_union = flight_union.union(fr)
        with self.check(
            "Subscription creation succeeds", dss_wrapper.participant_id
        ) as check:
            cs = dss_wrapper.put_sub(
                check,
                [flight_union.get_vertex(k) for k in range(4)],
                0,
                3000,
                datetime.now(),
                datetime.now() + timedelta(hours=1),
                self._mock_uss.base_url + "/mock/riddp",
                self._subscription_id,
                None,
            )
            if not cs.success:
                check.record_failed(
                    summary="Error while creating a Subscription for the Mock USS on the DSS",
                    details=f"Error message: {cs.errors}",
                )
                return

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
        evaluator = display_data_evaluator.RIDObservationEvaluator(
            self,
            self._injected_flights,
            config,
            self._rid_version,
            self._dss_pool.dss_instances[0] if self._dss_pool else None,
        )

        def poll_fct(rect: LatLngRect) -> bool:
            evaluator.evaluate_system_instantaneously(self._observers.observers, rect)
            return False

        virtual_observer.start_polling(
            config.min_polling_interval.timedelta,
            [
                self._rid_version.max_diagonal_km * 1000 + 500,  # too large
                self._rid_version.max_diagonal_km * 1000 - 100,  # clustered
                self._rid_version.max_details_diagonal_km * 1000 - 100,  # details
            ],
            poll_fct,
        )

    def _validate_mock_uss_notifications(self, scenario_start_time: datetime):
        interactions, q = self._mock_uss.get_interactions(Time(scenario_start_time))
        if q.status_code != 200:
            logger.error(
                f"Failed to get interactions from mock uss: HTTP {q.status_code} - {q.response.json}"
            )
            self.record_note(
                "mock_uss_interactions",
                f"failed to obtain interactions with http status {q.status_code}",
            )
            return

        logger.debug(
            f"Received {len(interactions)} interactions from mock uss:\n{interactions}"
        )

        # For each of the service providers we injected flights in,
        # we're looking for an inbound notification for the mock_uss's subscription:
        for test_flight in self._injected_flights:
            notification_reception_times = []
            with self.check(
                "Service Provider issued a notification", test_flight.uss_participant_id
            ) as check:
                notif_param_type = self._notif_param_type()
                sub_notif_interactions: List[(datetime, notif_param_type)] = [
                    (
                        i.query.request.received_at.datetime,
                        ImplicitDict.parse(i.query.request.json, notif_param_type),
                    )
                    for i in interactions
                    if i.query.request.method == "POST"
                    and i.direction == "Incoming"
                    and "/uss/identification_service_areas/" in i.query.request.url
                ]
                for (received_at, notification) in sub_notif_interactions:
                    for sub in notification.subscriptions:
                        if (
                            sub.subscription_id == self._subscription_id
                            and notification.service_area.owner
                            == test_flight.uss_participant_id
                        ):
                            notification_reception_times.append(received_at)

                if len(notification_reception_times) == 0:
                    check.record_failed(
                        summary="No notification received",
                        details=f"No notification received from {test_flight.uss_participant_id} for subscription {self._subscription_id} about flight {test_flight.test_id} that happened within the subscription's boundaries.",
                    )
                    continue

            # The performance requirements define 95th and 99th percentiles for the SP to respect,
            # which we can't strictly check with one (or very few) samples.
            # Furthermore, we use the time of injection as the 'starting point', which is necessarily before the SP
            # actually becomes aware of the subscription (when the ISA is created at the DSS)
            # the p95 to respect is 1 second, the p99 is 3 seconds.
            # As an approximation, we check that the single sample (or the average of the few) is below the p99.
            notif_latencies = [
                l - test_flight.query_timestamp for l in notification_reception_times
            ]
            avg_latency = (
                sum(notif_latencies, timedelta(0)) / len(notif_latencies)
                if notif_latencies
                else None
            )
            with self.check(
                "Service Provider notification was received within delay",
                test_flight.uss_participant_id,
            ) as check:
                if avg_latency.seconds > self._rid_version.dp_data_resp_percentile99_s:
                    check.record_failed(
                        summary="Notification received too late",
                        details=f"Notification(s) received {avg_latency} after the flight ended, which is more than the allowed 99th percentile of {self._rid_version.dp_data_resp_percentile99_s} seconds.",
                    )

    def _notif_param_type(
        self,
    ) -> Type[
        api_v19.PutIdentificationServiceAreaNotificationParameters
        | api_v22a.PutIdentificationServiceAreaNotificationParameters
    ]:
        if self._rid_version == RIDVersion.f3411_19:
            return api_v19.PutIdentificationServiceAreaNotificationParameters
        elif self._rid_version == RIDVersion.f3411_22a:
            return api_v22a.PutIdentificationServiceAreaNotificationParameters
        else:
            raise ValueError(f"Unsupported RID version: {self._rid_version}")

    def cleanup(self):
        self.begin_cleanup()

        self._dss_wrapper.cleanup_sub(self._subscription_id)

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
