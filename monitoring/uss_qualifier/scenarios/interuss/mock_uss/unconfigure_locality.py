from dataclasses import dataclass
from typing import List

from monitoring.monitorlib.locality import LocalityCode
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


@dataclass
class MockUSSLocalityConfiguration(object):
    client: MockUSSClient
    locality_code: LocalityCode


unconfigure_stack: List[List[MockUSSLocalityConfiguration]] = []
"""The stack of mock_uss locality configurations that have been performed by configure_locality.

UnconfigureLocality will reset localities according to the most recent stack addition."""


class UnconfigureLocality(TestScenario):
    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        if not unconfigure_stack:
            raise ValueError(
                "UnconfigureLocality attempted to access an empty stack of locality configurations; ConfigureLocality must be run first and UnconfigureLocality instances may not exceed ConfigureLocality instances"
            )
        to_unconfigure = unconfigure_stack.pop(-1)

        self.begin_test_case("Restore locality")

        self.begin_test_step("Set locality to old value")

        for instance in to_unconfigure:
            query = instance.client.set_locality(instance.locality_code)
            self.record_query(query)
            with self.check("Query ok", [instance.client.participant_id]) as check:
                if query.status_code != 200:
                    check.record_failed(
                        f"Set locality returned {query.status_code}",
                        Severity.Medium,
                        query_timestamps=[query.request.initiated_at.datetime],
                    )

        self.end_test_step()

        self.end_test_case()

        self.end_test_scenario()
