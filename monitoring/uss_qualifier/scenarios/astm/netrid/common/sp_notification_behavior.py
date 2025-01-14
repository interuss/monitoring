from datetime import timedelta
from typing import List, Optional, Type, Union

from future.backports.datetime import datetime
from implicitdict import ImplicitDict
from loguru import logger
from requests.exceptions import RequestException
from s2sphere import LatLngRect
from uas_standards.astm.f3411.v19 import api as api_v19
from uas_standards.astm.f3411.v22a import api as api_v22a

from monitoring.monitorlib.clients.mock_uss.interactions import QueryDirection
from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.temporal import Time
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3411.dss import (
    DSSInstancesResource,
    DSSInstanceResource,
)
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
from monitoring.uss_qualifier.scenarios.interuss.mock_uss.test_steps import (
    get_mock_uss_interactions,
    direction_filter,
    status_code_filter,
    operation_filter,
)
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class ServiceProviderNotificationBehavior(GenericTestScenario):
    SUB_TYPE = register_resource_type(399, "Subscription")

    _flights_data: FlightDataResource
    _service_providers: NetRIDServiceProviders
    _mock_uss: MockUSSClient

    _injected_flights: List[InjectedFlight]
    _injected_tests: List[InjectedTest]

    _dss_wrapper: Optional[DSSWrapper]
    _subscription_id: str

    def __init__(
        self,
        flights_data: FlightDataResource,
        service_providers: NetRIDServiceProviders,
        mock_uss: MockUSSResource,
        id_generator: IDGeneratorResource,
        dss_pool: DSSInstancesResource,
    ):
        super().__init__()
        self._flights_data = flights_data
        self._service_providers = service_providers
        self._mock_uss = mock_uss.mock_uss
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
        self.begin_test_step("Clean workspace")
        # Test flights are being taken care of by preparation step before this scenario
        self._dss_wrapper.cleanup_sub(self._subscription_id)
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Service Provider notification behavior")

        self.begin_test_step("Mock USS Subscription")
        self._subscribe_mock_uss()
        self.end_test_step()

        self.begin_test_step("Injection")
        self._inject_flights()
        self.end_test_step()

        self.begin_test_step("Validate Mock USS received notification")
        self._validate_mock_uss_notifications(context.start_time)
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _subscribe_mock_uss(self):
        # Get all bounding rects for flights
        flight_rects = [f.get_rect() for f in self._flights_data.get_test_flights()]
        flight_union: Optional[LatLngRect] = None
        for fr in flight_rects:
            if flight_union is None:
                flight_union = fr
            else:
                flight_union = flight_union.union(fr)
        with self.check(
            "Subscription creation succeeds", self._dss_wrapper.participant_id
        ) as check:
            cs = self._dss_wrapper.put_sub(
                check,
                [flight_union.get_vertex(k) for k in range(4)],
                self._rid_version.min_altitude_api,
                self._rid_version.max_altitude_api,
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
                    query_timestamps=cs.query_timestamps,
                )

    def _inject_flights(self):
        (self._injected_flights, self._injected_tests) = injection.inject_flights(
            self, self._flights_data, self._service_providers
        )

    def _validate_mock_uss_notifications(self, scenario_start_time: datetime):
        def post_isa_filter(interaction):
            return (
                interaction.query.request.method == "POST"
                and "/uss/identification_service_areas/"
                in interaction.query.request.url
            )

        interactions, _ = get_mock_uss_interactions(
            self,
            self._mock_uss,
            Time(scenario_start_time),
            direction_filter(QueryDirection.Incoming),
            status_code_filter(204),
            # Not relying on operation_filter because it currently only knows about ASTM F3548 operations
            post_isa_filter,
        )

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
                ]
                for (received_at, notification) in sub_notif_interactions:
                    for sub in notification.subscriptions:
                        if (
                            sub.subscription_id == self._subscription_id
                            and "service_area"
                            in notification  # deletion notification don't have this field
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
            avg_latency = sum(notif_latencies, timedelta(0)) / len(notif_latencies)
            with self.check(
                "Service Provider notification was received within delay",
                test_flight.uss_participant_id,
            ) as check:
                if avg_latency.seconds > self._rid_version.dp_data_resp_percentile99_s:
                    check.record_failed(
                        summary="Notification received too late",
                        details=f"Notification(s) received {avg_latency} after the flight ended, which is more than the allowed 99th percentile of {self._rid_version.dp_data_resp_percentile99_s} seconds.",
                    )

    def _notif_operation_id(self) -> Union[api_v19.OperationID | api_v22a.OperationID]:
        if self._rid_version.f3411_19:
            return api_v19.OperationID.PostIdentificationServiceArea
        elif self._rid_version.f3411_22a:
            return api_v22a.OperationID.PostIdentificationServiceArea
        else:
            raise ValueError(f"Unsupported RID version: {self._rid_version}")

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

        if self._dss_wrapper:
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
