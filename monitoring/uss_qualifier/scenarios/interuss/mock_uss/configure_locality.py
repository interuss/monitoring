from typing import List

from monitoring.monitorlib.locality import LocalityCode
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSsResource,
    MockUSSClient,
)
from monitoring.uss_qualifier.resources.interuss.mock_uss.locality import (
    LocalityResource,
)
from monitoring.uss_qualifier.scenarios.interuss.mock_uss.unconfigure_locality import (
    MockUSSLocalityConfiguration,
    unconfigure_stack,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class ConfigureLocality(TestScenario):
    mock_uss_instances: List[MockUSSClient]
    locality_code: LocalityCode
    to_unconfigure: List[MockUSSLocalityConfiguration]

    def __init__(
        self, mock_uss_instances: MockUSSsResource, locality: LocalityResource
    ):
        super(ConfigureLocality, self).__init__()
        self.mock_uss_instances = mock_uss_instances.mock_uss_instances
        self.locality_code = locality.locality_code
        self.to_unconfigure = []

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Set locality")

        self.begin_test_step("Get current locality value")
        old_locality_codes = {}
        for mock_uss in self.mock_uss_instances:
            locality_code, query = mock_uss.get_locality()
            self.record_query(query)
            with self.check("Query ok", [mock_uss.participant_id]) as check:
                if query.status_code != 200:
                    check.record_failed(
                        f"Get current locality returned {query.status_code}",
                        Severity.High,
                        query_timestamps=[query.request.initiated_at.datetime],
                    )
                elif locality_code is None:
                    check.record_failed(
                        f"Missing current locality code",
                        Severity.High,
                        "Query to get current locality value did not produce a valid locality code",
                        query_timestamps=[query.request.initiated_at.datetime],
                    )
            old_locality_codes[mock_uss] = locality_code
            self.record_note(
                mock_uss.session.get_prefix_url() + " old locality", locality_code
            )
        self.end_test_step()

        self.begin_test_step("Set locality to desired value")
        for mock_uss in self.mock_uss_instances:
            query = mock_uss.set_locality(self.locality_code)
            self.record_query(query)
            with self.check("Query ok", [mock_uss.participant_id]) as check:
                if query.status_code != 200:
                    check.record_failed(
                        f"Set locality returned {query.status_code}",
                        Severity.High,
                        query_timestamps=[query.request.initiated_at.datetime],
                    )
            self.to_unconfigure.append(
                MockUSSLocalityConfiguration(
                    client=mock_uss, locality_code=old_locality_codes[mock_uss]
                )
            )
        unconfigure_stack.append(self.to_unconfigure)
        self.to_unconfigure = []
        self.end_test_step()

        self.end_test_case()

        self.end_test_scenario()

    def cleanup(self):
        self.begin_cleanup()

        for instance in self.to_unconfigure:
            query = instance.client.set_locality(instance.locality_code)
            self.record_query(query)

        self.end_cleanup()
