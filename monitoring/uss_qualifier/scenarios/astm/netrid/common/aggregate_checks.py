import re

from loguru import logger

from monitoring.monitorlib import fetch
from monitoring.monitorlib.fetch import QueryType, evaluation
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.astm.f3411 import DSSInstancesResource
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstance
from monitoring.uss_qualifier.resources.dev import TestExclusionsResource
from monitoring.uss_qualifier.resources.netrid import (
    NetRIDObserversResource,
    NetRIDServiceProviders,
)
from monitoring.uss_qualifier.resources.netrid.observers import RIDSystemObserver
from monitoring.uss_qualifier.resources.netrid.service_providers import (
    NetRIDServiceProvider,
)
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class AggregateChecks(GenericTestScenario):
    _rid_version: RIDVersion
    _service_providers: list[NetRIDServiceProvider]
    _observers: list[RIDSystemObserver]
    _dss_instances: list[DSSInstance]

    _queries: list[fetch.Query]
    _participants_by_base_url: dict[str, ParticipantID] = dict()
    _allow_cleartext_queries: bool = False
    _queries_by_participant: dict[ParticipantID, list[fetch.Query]]

    def __init__(
        self,
        service_providers: NetRIDServiceProviders,
        dss_instances: DSSInstancesResource,
        observers: NetRIDObserversResource | None = None,
        test_exclusions: TestExclusionsResource | None = None,
    ):
        super().__init__()
        self._service_providers = service_providers.service_providers
        self._observers = observers.observers if observers else []
        self._dss_instances = dss_instances.dss_instances

        # identify SPs and observers by their base URL
        self._participants_by_base_url.update(
            {sp.injection_base_url: sp.participant_id for sp in self._service_providers}
        )

        self._participants_by_base_url.update(
            {dp.base_url: dp.participant_id for dp in self._observers}
        )

        if test_exclusions is not None:
            self._allow_cleartext_queries = test_exclusions.allow_cleartext_queries

    def _init_queries(self, context: ExecutionContext):
        self._queries = list(context.sibling_queries())

        # collect and classify queries by participant
        self._queries_by_participant = {
            participant: list()
            for participant in self._participants_by_base_url.values()
        }

        for query in self._queries:
            for base_url, participant in self._participants_by_base_url.items():
                if query.request.url.startswith(
                    base_url
                ) and not query.has_field_with_value("participant_id"):
                    query.participant_id = participant
                    break

            # Only consider queries with the participant/server explicitly identified
            if query.has_field_with_value("participant_id"):
                participant_queries = self._queries_by_participant.get(
                    query.participant_id, []
                )
                participant_queries.append(query)
                self._queries_by_participant[query.participant_id] = participant_queries

    def run(self, context: ExecutionContext):
        self._init_queries(context)

        self.begin_test_scenario(context)

        self.record_note("participants", str(self._participants_by_base_url))
        self.record_note("nb_queries", str(len(self._queries)))

        for sp in self._service_providers:
            self.record_note(
                "service_providers",
                f"configured service providers: {sp.participant_id} - {sp.injection_base_url}",
            )

        for o in self._observers:
            self.record_note(
                "observer", f"configured observer: {o.participant_id} - {o.base_url}"
            )

        # DP performance
        self.begin_test_case("Performance of Display Providers requests")
        self.begin_test_step("Performance of /display_data requests")

        self._dp_display_data_times_step()

        self.end_test_step()
        self.begin_test_step("Performance of /display_data/<flight_id> requests")
        self._dp_display_data_details_times_step()
        self.end_test_step()

        self.end_test_case()

        # SP performance
        self.begin_test_case("Performance of Service Providers requests")
        self.begin_test_step("Performance of /flights?view requests")

        self._sp_flights_area_times_step()

        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Verify https is in use")
        self.begin_test_step("Verify https is in use")

        self._verify_https_everywhere()

        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()

    def _verify_https_everywhere(self):
        if not self._allow_cleartext_queries:
            for (
                participant_id,
                participant_queries,
            ) in self._queries_by_participant.items():
                self._inspect_participant_queries(participant_id, participant_queries)
        else:
            self.record_note(
                "https-check",
                "cleartext queries are allowed by test exclusions, skipping HTTPS check",
            )

        # Check that all queries have been attributed to a participant
        unattr_queries = [
            f"{query.request.method} {query.request.url}"
            for query in self._queries
            if query.get("participant_id") is None
        ]
        query_list = "\n".join("  * " + q for q in unattr_queries)
        msg = f"Found unattributed queries:\n{query_list}"
        if len(unattr_queries) > 0:
            self.record_note("unattributed-queries", msg)
            logger.warning(msg)

    def _inspect_participant_queries(
        self, participant_id: str, participant_queries: list[fetch.Query]
    ):
        cleartext_queries = []
        for query in participant_queries:
            if query.request.url.startswith("http://"):
                cleartext_queries.append(query)
                logger.info(
                    f"query is not https: {participant_id} - {query.request.url}",
                )

        with self.check(
            "All interactions happen over https",
            [participant_id],
        ) as check:
            if len(cleartext_queries) > 0:
                timestamps = [
                    q.request.initiated_at.datetime for q in cleartext_queries
                ]
                urls = set([q.request.url for q in cleartext_queries])
                check.record_failed(
                    summary=f"found {len(cleartext_queries)} cleartext http queries",
                    details=f"unique cleartext urls: {urls}",
                    query_timestamps=timestamps,
                )

    def _dp_display_data_details_times_step(self):
        """
        Check performance of /display_data/<flight_id> requests and confirm they conform to
        NetDpDetailsResponse95thPercentile (2s) and NetDpDetailsResponse99thPercentile (6s)
        """
        for participant, all_queries in self._queries_by_participant.items():
            relevant_queries: list[fetch.Query] = list()
            for query in all_queries:
                if (
                    query.status_code == 200
                    and query.has_field_with_value("query_type")
                    and query.query_type == QueryType.InterUSSRIDObservationV1GetDetails
                ):
                    relevant_queries.append(query)

            if len(relevant_queries) == 0:
                # this may be a service provider
                self.record_note(
                    f"{participant}/display_data/<flight_id>",
                    "skipped check: no relevant queries",
                )
                continue

            # compute percentiles
            durations = [query.response.elapsed_s for query in relevant_queries]
            [p95, p99] = evaluation.compute_percentiles(durations, [95, 99])
            with self.check(
                "Performance of /display_data/<flight_id> requests", [participant]
            ) as check:
                if p95 > self._rid_version.dp_details_resp_percentile95_s:
                    check.record_failed(
                        summary="95th percentile of durations for DP display_data details queries is higher than threshold",
                        details=f"threshold: {self._rid_version.dp_details_resp_percentile95_s}s, 95th percentile: {p95:.3g}s",
                    )
                if p99 > self._rid_version.dp_details_resp_percentile99_s:
                    check.record_failed(
                        summary="99th percentile of durations for DP display_data details queries is higher than threshold",
                        details=f"threshold: {self._rid_version.dp_details_resp_percentile99_s}s, 99th percentile: {p99:.3g}s",
                    )

            self.record_note(
                f"{participant}/display_data/<flight_id>",
                f"{participant}/display_data/<flight_id> stats computed on {len(durations)} queries "
                f"95th percentile: {p95:.3g}s, 99th percentile: {p99:.3g}s",
            )

    def _sp_flights_area_times_step(self):
        for participant, all_queries in self._queries_by_participant.items():
            # identify successful flights queries
            relevant_queries: list[fetch.Query] = list()
            for query in all_queries:
                if query.has_field_with_value("query_type") and (
                    # TODO find a cleaner way than checking for version here
                    query.query_type == QueryType.F3411v19USSSearchFlights
                    or query.query_type == QueryType.F3411v22aUSSSearchFlights
                ):
                    relevant_queries.append(query)

            if len(relevant_queries) == 0:
                # this may be a display provider
                self.record_note(
                    f"{participant}/flights", "skipped check: no relevant queries"
                )

                continue

            # Collect query durations
            durations = [query.response.elapsed_s for query in relevant_queries]
            (p95, p99) = evaluation.compute_percentiles(durations, [95, 99])

            with self.check("95th percentile response time", [participant]) as check:
                if p95 > self._rid_version.sp_data_resp_percentile95_s:
                    check.record_failed(
                        summary=f"95th percentile of /flights?view requests is {p95:.3g} s",
                        details=f"expected less than {self._rid_version.sp_data_resp_percentile95_s} s, was {p95:.3g}",
                    )
            with self.check("99th percentile response time", [participant]) as check:
                if p99 > self._rid_version.sp_data_resp_percentile99_s:
                    check.record_failed(
                        summary=f"99th percentile of /flights?view requests is {p99:.3g} s",
                        details=f"expected less than {self._rid_version.sp_data_resp_percentile99_s} s, was {p99:.3g}",
                    )

            self.record_note(
                f"{participant}/flights",
                f"percentiles on {len(relevant_queries)} relevant queries: 95th: {p95:.3g}; 99th: {p99:.3g}",
            )

    def _dp_display_data_times_step(self):
        """
        :return: the query durations of respectively the initial queries and the subsequent ones
        """

        pattern = re.compile(r"/display_data\?view=(-?\d+(.\d+)?,){3}-?\d+(.\d+)?")
        for participant, all_queries in self._queries_by_participant.items():
            # identify successful display_data queries
            relevant_queries: list[fetch.Query] = list()
            for query in all_queries:
                match = pattern.search(query.request.url)
                if match is not None and query.status_code == 200:
                    relevant_queries.append(query)

            if len(relevant_queries) == 0:
                # this may be a service provider
                self.record_note(
                    f"{participant}/display_data", "skipped check: no relevant queries"
                )
                continue

            # compute percentiles
            relevant_queries_by_url = evaluation.classify_query_by_url(relevant_queries)
            (
                init_durations,
                subsequent_durations,
            ) = evaluation.get_init_subsequent_queries_durations(
                self._rid_version.min_session_length_s, relevant_queries_by_url
            )
            [init_95th, init_99th] = evaluation.compute_percentiles(
                init_durations, [95, 99]
            )
            [subsequent_95th, subsequent_99th] = evaluation.compute_percentiles(
                subsequent_durations, [95, 99]
            )

            with self.check(
                "Performance of /display_data initial requests", [participant]
            ) as check:
                if init_95th > self._rid_version.dp_init_resp_percentile95_s:
                    check.record_failed(
                        summary="95th percentile of durations for initial DP display_data queries is higher than threshold",
                        details=f"threshold: {self._rid_version.dp_init_resp_percentile95_s}, 95th percentile: {init_95th:.3g}",
                    )
                if init_99th > self._rid_version.dp_init_resp_percentile99_s:
                    check.record_failed(
                        summary="99th percentile of durations for initial DP display_data queries is higher than threshold",
                        details=f"threshold: {self._rid_version.dp_init_resp_percentile99_s}, 99th percentile: {init_99th:.3g}",
                    )

            with self.check(
                "Performance of /display_data subsequent requests", [participant]
            ) as check:
                if subsequent_95th > self._rid_version.dp_data_resp_percentile95_s:
                    check.record_failed(
                        summary="95th percentile of durations for subsequent DP display_data queries is higher than threshold",
                        details=f"threshold: {self._rid_version.dp_data_resp_percentile95_s}, 95th percentile: {subsequent_95th:.3g}",
                    )
                if subsequent_99th > self._rid_version.dp_data_resp_percentile99_s:
                    check.record_failed(
                        summary="99th percentile of durations for subsequent DP display_data queries is higher than threshold",
                        details=f"threshold: {self._rid_version.dp_data_resp_percentile99_s}, 95th percentile: {subsequent_99th:.3g}",
                    )

            self.record_note(
                f"{participant}/display_data",
                f"percentiles on {len(relevant_queries)} relevant queries ({len(relevant_queries_by_url)} different URLs, {len(init_durations)} initial queries, {len(subsequent_durations)} subsequent queries): init 95th: {init_95th:.3g}; init 99th: {init_99th:.3g}; subsequent 95th: {subsequent_95th:.3g}; subsequent 99th: {subsequent_99th:.3g}",
            )

            self.record_note(
                f"{participant}/display_data details",
                f"Initial durations: {init_durations} subsequent durations: {subsequent_durations}",
            )
