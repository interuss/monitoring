from typing import List

from monitoring.uss_qualifier.resources.interuss.crdb import (
    CockroachDBClusterResource,
    CockroachDBNode,
)
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class CRDBAccess(GenericTestScenario):
    crdb_nodes: List[CockroachDBNode] = []

    def __init__(
        self,
        crdb_cluster: CockroachDBClusterResource,
    ):
        super().__init__()
        for node in crdb_cluster.nodes:
            self.crdb_nodes.append(node.get_client())

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self._setup()
        self.end_test_case()

        self.begin_test_case("Verify security interoperability")
        self._attempt_connection()
        self.end_test_case()

        self.end_test_scenario()

    def _setup(self) -> None:
        self.begin_test_step("Validate nodes are reachable")
        for node in self.crdb_nodes:
            with self.check(
                "Node is reachable",
                node.participant_id,
            ) as check:
                reachable, e = node.is_reachable()
                if not reachable:
                    check.record_failed(
                        "Node is not reachable",
                        details=f"Error message: {e}",
                    )

        self.end_test_step()

    def _attempt_connection(self) -> None:
        self.begin_test_step("Attempt to connect in insecure mode")
        for node in self.crdb_nodes:
            with self.check(
                "Node runs in secure mode",
                node.participant_id,
            ) as check:
                secure_mode, e = node.runs_in_secure_mode()
                if not secure_mode:
                    check.record_failed(
                        "Node is not in secure mode",
                        details=f"Reported connection error (if any): {e}",
                    )
        self.end_test_step()

        self.begin_test_step("Attempt to connect with legacy encryption protocol")
        for node in self.crdb_nodes:
            with self.check(
                "Node rejects legacy encryption protocols",
                node.participant_id,
            ) as check:
                rejected, e = node.legacy_ssl_version_rejected()
                if not rejected:
                    check.record_failed(
                        "Node did not reject connection with legacy encryption protocol",
                        details=f"Reported connection error (if any): {e}",
                    )
        self.end_test_step()
