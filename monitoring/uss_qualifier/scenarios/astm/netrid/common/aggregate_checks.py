import re
import statistics
from operator import attrgetter
from typing import List, Dict, Tuple, Union

from monitoring.monitorlib import fetch
from monitoring.monitorlib.fetch.evaluation import compute_query_durations_percentiles
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.scenarios.interuss.evaluation_scenario import (
    ReportEvaluationScenario,
)

from monitoring.uss_qualifier.resources.interuss.report import TestSuiteReportResource
from monitoring.uss_qualifier.resources.netrid import (
    NetRIDServiceProviders,
    NetRIDObserversResource,
)
from monitoring.uss_qualifier.resources.netrid.observers import RIDSystemObserver
from monitoring.uss_qualifier.resources.netrid.service_providers import (
    NetRIDServiceProvider,
)


class AggregateChecks(ReportEvaluationScenario):
    _rid_version: RIDVersion
    _service_providers: List[NetRIDServiceProvider]
    _observers: List[RIDSystemObserver]

    _queries: List[fetch.Query]
    _participants_by_base_url: Dict[str, ParticipantID] = dict()
    _queries_by_participant: Dict[ParticipantID, List[fetch.Query]]

    def __init__(
        self,
        report_resource: TestSuiteReportResource,
        service_providers: NetRIDServiceProviders,
        observers: NetRIDObserversResource,
    ):
        super().__init__(report_resource)
        self._queries = self.report.queries()
        self._service_providers = service_providers.service_providers
        self._observers = observers.observers

        # identify SPs and observers by their base URL
        self._participants_by_base_url.update(
            {sp.base_url: sp.participant_id for sp in self._service_providers}
        )
        self._participants_by_base_url.update(
            {dp.base_url: dp.participant_id for dp in self._observers}
        )

        # collect and classify queries by participant
        self._queries_by_participant = {
            participant: list()
            for participant in self._participants_by_base_url.values()
        }
        for query in self._queries:
            for base_url, participant in self._participants_by_base_url.items():
                if query.request.url.startswith(base_url):

                    # TODO: debugging attempt (there is a str amongst the fetch.Query)
                    print(f"{type(query)}")
                    if type(query) == str:
                        print(query)
                    self._queries_by_participant[participant] += query
                    break

    def run(self):
        self.begin_test_scenario()
        self.record_note("participants", str(self._participants_by_base_url))
        self.record_note("nb_queries", str(len(self._queries)))

        self.begin_test_case("Time performances of Display Provider requests")

        self.begin_test_step("Display data requests")
        self._dp_display_data_times_step()
        self.end_test_step()

        self.end_test_case()

        # SP response times NET0260.a
        # flight details resp times NET0460
        # perfs of SP pushing to DP NET0740

        # Service Provider response times logged
        #   Each USS being tested as a Service Provider logged, for all incoming Display Provider requests that resulted in responses that did not indicate an error:
        #   The earliest timestamp at which a Display Provider request was received
        #   The latest timestamp before the response was dispatched
        #   The client ID of the querying Display Provider
        #   The URL of the endpoint being queried
        # Display Provider requests logged
        #   Each USS being tested as a Display Provider (or acting in the Qualifier role) logged, for all outgoing requests to Service Providers that did not indicate an error:
        #   The latest timestamp before a request to a Service Provider was dispatched
        #   The earliest timestamp after a response from the Service Provider was received
        #   The URL of the Service Provider endpoint being queried
        # Display Provider responses logged
        #   Each USS being tested as a Display Provider logged, for all incoming requests from a Display Application or Test Driver that did not indicate an error:
        #   The earliest timestamp at which the Display Application or Test Driver request was received
        #   The latest timestamp before the response was dispatched
        #   The view bounds, for area-based queries

        self.end_test_scenario()

    def _dp_display_data_times_step(self):
        """
        :return: the query durations of respectively the initial queries and the subsequent ones
        """

        # find successful display_data queries for each DP
        pattern = re.compile(r"/display_data\?view=(-?\d+(.\d+)?,){3}-?\d+(.\d+)?")
        for participant, all_queries in self._queries_by_participant.items():

            relevant_queries: List[fetch.Query] = list()
            for query in all_queries:

                # TODO: debugging attempt (there is a str amongst the fetch.Query)
                print(f"{type(query)}")
                if type(query) == str:
                    print(query)

                match = pattern.search(query.request.url)
                if match is not None and query.status_code == 200:
                    relevant_queries += query

            (
                init_95th,
                init_99th,
                subsequent_95th,
                subsequent_99th,
            ) = compute_query_durations_percentiles(
                self._rid_version.min_session_length_s, relevant_queries
            )

            with self.check("TODO: NET0420", [participant]) as check:
                if init_95th > self._rid_version.dp_init_resp_percentile95_s:
                    check.record_failed(
                        summary=f"95th percentile of durations for initial DP display_data queries is higher than threshold",
                        severity=Severity.Medium,
                        participants=[participant],
                        details=f"threshold: {self._rid_version.dp_init_resp_percentile95_s}, 95th percentile: {init_95th}",
                    )
                if init_99th > self._rid_version.dp_init_resp_percentile99_s:
                    check.record_failed(
                        summary=f"99th percentile of durations for initial DP display_data queries is higher than threshold",
                        severity=Severity.Medium,
                        participants=[participant],
                        details=f"threshold: {self._rid_version.dp_init_resp_percentile99_s}, 99th percentile: {init_99th}",
                    )

            with self.check("TODO: NET0440", [participant]) as check:
                if subsequent_95th > self._rid_version.dp_data_resp_percentile95_s:
                    check.record_failed(
                        summary=f"95th percentile of durations for subsequent DP display_data queries is higher than threshold",
                        severity=Severity.Medium,
                        participants=[participant],
                        details=f"threshold: {self._rid_version.dp_data_resp_percentile95_s}, 95th percentile: {subsequent_95th}",
                    )
                if subsequent_99th > self._rid_version.dp_data_resp_percentile99_s:
                    check.record_failed(
                        summary=f"99th percentile of durations for subsequent DP display_data queries is higher than threshold",
                        severity=Severity.Medium,
                        participants=[participant],
                        details=f"threshold: {self._rid_version.dp_data_resp_percentile99_s}, 95th percentile: {subsequent_99th}",
                    )
