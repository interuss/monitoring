from collections.abc import Callable
from datetime import timedelta
from typing import TypeVar

from future.backports.datetime import datetime
from implicitdict import ImplicitDict
from requests.exceptions import RequestException
from s2sphere import LatLngRect
from uas_standards.astm.f3411.v19 import api as api_v19
from uas_standards.astm.f3411.v22a import api as api_v22a

from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    QueryDirection,
)
from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.temporal import Time
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstancesResource
from monitoring.uss_qualifier.resources.interuss import IDGeneratorResource
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSClient,
    MockUSSResource,
)
from monitoring.uss_qualifier.resources.netrid import (
    FlightDataResource,
    NetRIDServiceProviders,
)
from monitoring.uss_qualifier.scenarios.astm.netrid import injection
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.astm.netrid.injection import (
    InjectedFlight,
    InjectedTest,
)
from monitoring.uss_qualifier.scenarios.interuss.mock_uss.test_steps import (
    direction_filter,
    get_mock_uss_interactions,
    status_code_filter,
)
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

TOperationResult = TypeVar("TOperationResult")


class ServiceProviderNotificationBehavior(GenericTestScenario):
    SUB_TYPE = register_resource_type(399, "Subscription")

    _flights_data: FlightDataResource
    _service_providers: NetRIDServiceProviders
    _mock_uss: MockUSSClient

    _injected_flights: list[InjectedFlight]
    _injected_tests: list[InjectedTest]

    _dss_wrapper: DSSWrapper | None
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
        # Given that we know when flights are injected, we could narrow down the time window for
        # which we are looking for notifications to something more precise than scenario start time.
        # TODO tracked in #1052
        self._validate_mock_uss_notifications(context.start_time)
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _subscribe_mock_uss(self):
        # Get all bounding rects for flights
        flight_rects = [f.get_rect() for f in self._flights_data.get_test_flights()]
        flight_union: LatLngRect | None = None
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

    def _validate_mock_uss_notifications(self, notifications_received_after: datetime):
        """verify that required notifications have been received within the permissible delay."""

        # Participants we injected flights in
        relevant_participant_ids = set(
            [tf.uss_participant_id for tf in self._injected_flights]
        )

        def post_isa_filter(interaction: Interaction):
            return (
                interaction.query.request.method == "POST"
                and "/uss/identification_service_areas/"
                in interaction.query.request.url
            )

        def fetch_interactions() -> list[Interaction]:
            return get_mock_uss_interactions(
                self,
                self._mock_uss,
                Time(notifications_received_after),
                direction_filter(QueryDirection.Incoming),
                status_code_filter(204),
                post_isa_filter,
            )[0]

        def includes_all_notifications(raw_interactions: list[Interaction]) -> bool:
            pids_having_notified = self._relevant_notified_subs(
                raw_interactions, relevant_participant_ids, notifications_received_after
            )
            # We're done once we have a notification from each SP we injected a flight in
            return len(pids_having_notified) == len(relevant_participant_ids)

        # notifications are not immediate: we optimistically try early, and retry until
        # the permissible delay has passed, or we have received all notifications.
        interactions = self._retry_with_backoff(
            fetch_interactions,
            retries=3,
            delay_s=1,
            delay_reason="waiting for expected notifications to be delivered",
            was_successful=includes_all_notifications,
        )
        # fish out the notification times per participant ID
        notifs_by_participant = self._relevant_notified_subs(
            interactions, relevant_participant_ids, notifications_received_after
        )
        # For each of the service providers we injected flights in,
        # check that we received a notification. We don't check the latency as a single datapoint does not allow
        # us to reach meaningful conclusions, but the check will fail if no notification was received for any SP
        # in which a flight was injected in during the roughly 3 seconds (at most) where we were waiting for them.
        for test_flight in self._injected_flights:
            with self.check(
                "Service Provider notification was received",
                test_flight.uss_participant_id,
            ) as check:
                notif_reception_times = notifs_by_participant.get(
                    test_flight.uss_participant_id, []
                )

                if len(notif_reception_times) == 0:
                    check.record_failed(
                        summary="No notification received",
                        details=f"No notification received within roughly {self._rid_version.dp_data_resp_percentile99_s} seconds from {test_flight.uss_participant_id} for subscription {self._subscription_id} about flight {test_flight.test_id} that happened within the subscription's boundaries.",
                    )
                    continue

    def _notif_operation_id(self) -> api_v19.OperationID | api_v22a.OperationID:
        if self._rid_version.f3411_19:
            return api_v19.OperationID.PostIdentificationServiceArea
        elif self._rid_version.f3411_22a:
            return api_v22a.OperationID.PostIdentificationServiceArea
        else:
            raise ValueError(f"Unsupported RID version: {self._rid_version}")

    def _notif_param_type(
        self,
    ) -> type[
        api_v19.PutIdentificationServiceAreaNotificationParameters
        | api_v22a.PutIdentificationServiceAreaNotificationParameters
    ]:
        if self._rid_version == RIDVersion.f3411_19:
            return api_v19.PutIdentificationServiceAreaNotificationParameters
        elif self._rid_version == RIDVersion.f3411_22a:
            return api_v22a.PutIdentificationServiceAreaNotificationParameters
        else:
            raise ValueError(f"Unsupported RID version: {self._rid_version}")

    def _relevant_notified_subs(
        self,
        raw_interactions: list[Interaction],
        relevant_pids: set[str],
        received_after: datetime,
    ) -> dict[str, list[datetime]]:
        # Parse version-specific notification parameters
        PutIsaParamsType = self._notif_param_type()

        relevant = []
        for interaction in raw_interactions:
            received_at = interaction.query.request.received_at.datetime
            notification: PutIsaParamsType = ImplicitDict.parse(
                interaction.query.request.json, PutIsaParamsType
            )
            for sub in notification.subscriptions:
                if (
                    sub.subscription_id == self._subscription_id
                    and "service_area"
                    in notification  # deletion notification don't have this field
                    and notification.service_area.owner in relevant_pids
                    # We may sometimes receive slightly older and unrelated notifications which we filter out
                    and received_at > received_after
                ):
                    relevant.append((received_at, notification.service_area.owner))

        notifs_by_participant: dict[str, list[datetime]] = {}
        for received_at, participant_id in relevant:
            if participant_id not in notifs_by_participant:
                notifs_by_participant[participant_id] = []
            notifs_by_participant[participant_id].append(received_at)
        return notifs_by_participant

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

    def _retry_with_backoff(
        self,
        operation: Callable[[], TOperationResult],
        retries: int,
        delay_s: float,
        delay_reason: str,
        was_successful: Callable[[TOperationResult], bool],
    ) -> TOperationResult:
        """Retry an operation with a delay, up to a certain number of retries,
        until the condition is met or retries are exhausted.
        """
        result = operation()
        for attempt in range(retries):
            if was_successful(result):
                return result
            self.sleep(timedelta(seconds=delay_s), delay_reason)
            result = operation()
        return result
