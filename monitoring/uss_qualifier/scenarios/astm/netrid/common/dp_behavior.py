import math
from datetime import datetime, timedelta
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

import arrow
import s2sphere
from s2sphere import LatLngRect, Angle

from monitoring.monitorlib import geo
from monitoring.monitorlib.clients.mock_uss.interactions import (
    QueryDirection,
    Interaction,
)
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.temporal import Time
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3411.dss import (
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.interuss import IDGeneratorResource
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSResource,
    MockUSSClient,
)
from monitoring.uss_qualifier.resources.interuss.uss_identification import (
    USSIdentificationResource,
)
from monitoring.uss_qualifier.resources.netrid import (
    NetRIDObserversResource,
    ServiceAreaResource,
)
from monitoring.uss_qualifier.resources.netrid.observers import RIDSystemObserver
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.interuss.mock_uss.test_steps import (
    get_mock_uss_interactions,
    direction_filter,
)
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class DisplayProviderBehavior(GenericTestScenario):
    """
    A scenario that attempts to cause a Display Provider to misbehave.
    """

    SUB_TYPE = register_resource_type(400, "ISA")

    _observers: List[RIDSystemObserver]
    _mock_uss: MockUSSClient

    _dss_wrapper: Optional[DSSWrapper]
    _isa_id: str
    _isa_area: List[s2sphere.LatLng]

    _identification: Optional[USSIdentificationResource]

    def __init__(
        self,
        observers: NetRIDObserversResource,  # Display providers being tested
        mock_uss: MockUSSResource,  # Mock USS playing the role of an SP
        id_generator: IDGeneratorResource,  # provides the ISA IS to be used
        dss_pool: DSSInstancesResource,
        isa: ServiceAreaResource,  # area for which the ISA is created
        uss_identification: Optional[USSIdentificationResource] = None,
    ):
        super().__init__()
        self._observers = observers.observers
        self._mock_uss = mock_uss.mock_uss
        self._dss_wrapper = DSSWrapper(self, dss_pool.dss_instances[0])
        self._isa_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._isa = isa.specification
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]
        self._identification = uss_identification

        isa_center = geo.center_of_mass(self._isa_area)
        degree_per_km = 360 / geo.EARTH_CIRCUMFERENCE_KM

        # A 1km by 1km square that has a diagonal below the allowed maximum:
        # Note that convolve_with_cap is used to expand the point to a square
        # (you might be tempted to use expanded() but it's not what we need here)
        self._small_rect = LatLngRect.from_point(isa_center).convolve_with_cap(
            Angle.from_degrees(1 * degree_per_km)
        )

        limit_side_km = self._rid_version.max_diagonal_km / math.sqrt(2)
        self._limit_rect = LatLngRect.from_point(isa_center).convolve_with_cap(
            Angle.from_degrees(limit_side_km * degree_per_km / 2)
        )
        # Make sure the limit_rect is close to the allowed diagonal limit
        assert (
            self._rid_version.max_diagonal_km * 0.99
            < geo.get_latlngrect_diagonal_km(self._limit_rect)
            <= self._rid_version.max_diagonal_km
        ), f"{geo.get_latlngrect_diagonal_km(self._limit_rect)} > {self._rid_version.max_diagonal_km}"

        # Make the too big rect 1% larger than the allowed diagonal limit
        self._too_big_rect = LatLngRect.from_point(isa_center).convolve_with_cap(
            Angle.from_degrees(limit_side_km * 1.01 * degree_per_km / 2)
        )
        assert (
            geo.get_latlngrect_diagonal_km(self._too_big_rect)
            > self._rid_version.max_diagonal_km
        ), f"{geo.get_latlngrect_diagonal_km(self._too_big_rect)} <= {self._rid_version.max_diagonal_km}"

    @property
    def _rid_version(self) -> RIDVersion:
        raise NotImplementedError(
            "NominalBehavior test scenario subclass must specify _rid_version"
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self.begin_test_step("Clean workspace")
        self._clean_isa()
        self.end_test_step()
        self.end_test_case()

        # TODO: Implement Subscription priming test case

        self.begin_test_case("Create flight")
        self.begin_test_step("Create ISA")
        # Create an ISA that points to the mock_uss playing the role of an SP
        self._step_create_isa()
        self.end_test_step()
        self.end_test_case()

        for obs in self._observers:
            test_case_start_time = arrow.utcnow().datetime
            # We run the entire test case for each provided observer
            # (Otherwise we can't differentiate which queries are from which observer)
            self.begin_test_case("Display Provider Behavior")

            self.begin_test_step("Query acceptable diagonal area")
            # Query the DP for the exact area of the ISA
            self._step_query_ok_diagonal(obs)
            self.end_test_step()

            self.begin_test_step("Query maximum diagonal area")
            # Query the DP with the maximum diagonal area
            self._step_query_maximum_diagonal(obs)
            self.end_test_step()

            self.begin_test_step("Query too long diagonal")
            self._step_query_too_big_diagonal(obs)
            self.end_test_step()

            self.begin_test_step("Verify query to SP")
            self._step_validate_queries_to_sp(obs, test_case_start_time)
            self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _mock_sp_base_url(self):
        if self._rid_version == RIDVersion.f3411_19:
            return self._mock_uss.base_url + "/mock/ridsp"
        elif self._rid_version == RIDVersion.f3411_22a:
            return self._mock_uss.base_url + "/mock/ridsp/v2"

    def _step_create_isa(self):

        start_time = arrow.utcnow().datetime
        end_time = start_time + timedelta(minutes=5)

        with self.check("Create an ISA", [self._dss_wrapper.participant_id]) as check:
            isa_change = self._dss_wrapper.put_isa(
                main_check=check,
                area_vertices=self._isa_area,
                start_time=start_time,
                end_time=end_time,
                uss_base_url=self._mock_sp_base_url(),
                isa_id=self._isa_id,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
                isa_version=None,
            )
            self._isa_version = isa_change.dss_query.isa.version

    def _step_query_ok_diagonal(self, observer: RIDSystemObserver):
        with self.check(
            "Observation query succeeds",
            [observer.participant_id],
        ) as check:
            observation, query = observer.observe_system(self._small_rect)
            if query.status_code != 200:
                check.record_failed(
                    summary="Query to display provider failed",
                    details=f"Valid observation query failed with status code {query.status_code}: {query.error_message}",
                    query_timestamps=[query.timestamp],
                )

    def _step_query_maximum_diagonal(self, observer: RIDSystemObserver):
        with self.check(
            "Maximum diagonal area query succeeds",
            [observer.participant_id],
        ) as check:
            observation, query = observer.observe_system(self._limit_rect)
            if query.status_code != 200:
                check.record_failed(
                    summary="Query to display provider failed",
                    details=f"Valid observation query failed with status code {query.status_code}: {query.error_message}",
                    query_timestamps=[query.timestamp],
                )

    def _step_query_too_big_diagonal(self, observer: RIDSystemObserver):
        with self.check(
            "Too long diagonal query fails",
            [observer.participant_id],
        ) as check:
            observation, query = observer.observe_system(self._too_big_rect)
            if not (400 <= query.status_code < 500):
                check.record_failed(
                    summary="Query to display provider succeeded",
                    details=f"Invalid observation query succeeded with status code {query.status_code}: {query.error_message}",
                    query_timestamps=[query.timestamp],
                )

    def _step_validate_queries_to_sp(
        self, observer: RIDSystemObserver, test_case_start_time: datetime
    ):
        def flight_search_filter(interaction: Interaction) -> bool:
            return (
                "/uss/flights?view=" in interaction.query.request.url
                and interaction.query.request.method == "GET"
            )

        interactions, q = get_mock_uss_interactions(
            self,
            self._mock_uss,
            Time(test_case_start_time),
            direction_filter(QueryDirection.Incoming),
            flight_search_filter,
        )

        with self.check("DP queried SP", observer.participant_id) as check:
            if len(interactions) == 0:
                check.record_failed(
                    summary="No queries to SP",
                    details=f"No queries to SP were found from the observer under test for participant {observer.participant_id}",
                    query_timestamps=[q.timestamp],
                )
                return

            if len(interactions) < 2:
                check.record_failed(
                    summary="Expected at least two queries to SP",
                    details=f"Found less than two queries to SP from observer under test for participant {observer.participant_id}",
                    query_timestamps=[q.timestamp],
                )

        with self.check(
            "No query to SP exceeded the maximum diagonal", observer.participant_id
        ) as check:
            # The requested are is url-encoded, eg:
            # <base_url>/uss/flights?view=37.17781782172688,-80.60691130981752,37.22228217827311,-80.55108869018248&recent_positions_duration=60"
            for fq in interactions:
                parsed_url = urlparse(fq.query.request.url)
                query_params = parse_qs(parsed_url.query)
                view_rect = geo.make_latlng_rect(query_params["view"][0])
                if (
                    geo.get_latlngrect_diagonal_km(view_rect)
                    > self._rid_version.max_diagonal_km
                ):
                    check.record_failed(
                        summary="Query to SP exceeded the maximum diagonal",
                        details=f"Query to SP from observer under test for participant {observer.participant_id} exceeded the maximum diagonal.",
                        query_timestamps=[q.timestamp],
                    )

    def _clean_isa(self):
        with self.check(
            "Removed pre-existing ISA",
            self._dss_wrapper.participant_id,
        ) as check:
            self._dss_wrapper.cleanup_isa(check, self._isa_id)

    def cleanup(self):
        self.begin_cleanup()
        self._clean_isa()
        self.end_cleanup()
