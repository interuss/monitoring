from monitoring.monitorlib.clients.versioning.client import VersionQueryError
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.versioning import SystemIdentityResource
from monitoring.uss_qualifier.resources.versioning.client import (
    VersionProvidersResource,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class GetSystemVersions(TestScenario):
    def __init__(
        self,
        version_providers: VersionProvidersResource,
        system_identity: SystemIdentityResource,
    ):
        super(GetSystemVersions, self).__init__()
        self._version_providers = version_providers.version_providers
        self._system_identity = system_identity.system_identity

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Get versions")
        self.begin_test_step("Get versions")

        for version_provider in self._version_providers:
            with self.check(
                "Valid response", participants=[version_provider.participant_id]
            ) as check:
                try:
                    resp = version_provider.get_version(self._system_identity)
                    self.record_query(resp.query)
                    self.record_note(
                        version_provider.participant_id,
                        f"{self._system_identity}={resp.version}",
                    )
                except VersionQueryError as e:
                    for q in e.queries:
                        self.record_query(q)
                    check.record_failed(
                        summary="Error querying version",
                        details=str(e),
                        severity=Severity.High,
                        query_timestamps=[q.request.timestamp for q in e.queries],
                    )

        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()
