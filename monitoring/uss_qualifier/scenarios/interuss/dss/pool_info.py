from uas_standards.interuss.automated_testing.versioning.constants import (
    Scope as VersioningScope,
)
from uas_standards.interuss.dss.aux.constants import Scope as AuxScope

from monitoring.monitorlib.clients.interuss.dss import InterUSSDSSClient
from monitoring.monitorlib.clients.versioning.client_interuss import (
    InterUSSVersioningClient,
    VersionQueryError,
)
from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class PoolInfo(GenericTestScenario):
    def __init__(
        self,
    ):
        super().__init__()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("aux information")

        self.begin_test_step("Examine versions")
        self._examine_versions()
        self.end_test_step()

        self.begin_test_step("Examine pool")
        self._examine_pool()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _examine_versions(self):
        for dss_instance in self._dss_instances:
            versioning_instance = dss_instance.get_instance({
                VersioningScope.ReadSystemVersions: "Read system version"
            })
            versioning_client = InterUSSVersioningClient(
                session=versioning_instance.client,
                participant_id=dss_instance.participant_id,
            )
            with self.check("Version obtained successfully", [dss_instance.participant_id]) as check:
                try:
                    version_resp = versioning_client.get_version("dss")
                    self.record_query(version_resp.query)
                    self.record_note(f"{dss_instance.participant_id} version", version_resp.version)
                except VersionQueryError as e:
                    self.record_queries(e.queries)
                    check.record_failed(
                        summary=f"Failed to get version from DSS instance {dss_instance.participant_id}",
                        details=str(e),
                        queries=e.queries,
                    )

    def _examine_pool(self):
        dar_ids = {}
        for dss_instance in self._dss_instances:
            aux_instance = dss_instance.get_instance({
                AuxScope.PoolStatusRead: "Read DSS pool status"
            })
            dss_client = InterUSSDSSClient(
                session=aux_instance.client,
                participant_id=dss_instance.participant_id,
            )
            with self.check("Pool information obtained successfully", [dss_instance.participant_id]) as check:
                try:
                    pool_resp, query = dss_client.get_pool()
                    self.record_query(query)
                    dar_id = pool_resp.dar_id if pool_resp.has_field_with_value("dar_id") else None
                    dar_ids[dss_instance.participant_id] = dar_id
                    self.record_note(f"{dss_instance.participant_id} DAR ID", dar_id or "None")
                except QueryError as e:
                    self.record_queries(e.queries)
                    check.record_failed(
                        summary=f"Failed to get pool info from DSS instance {dss_instance.participant_id}",
                        details=str(e),
                        queries=e.queries,
                    )

        # Compare DAR IDs
        reported_dar_ids = {pid: dar_id for pid, dar_id in dar_ids.items() if dar_id}
        with self.check("DAR ID matches", participants) as check:
            if len(set(reported_dar_ids.values())) > 1:
                participants = list(reported_dar_ids.keys())
                details = "\n".join(f"- {pid}: {dar_id}" for pid, dar_id in reported_dar_ids.items())
                check.record_failed(
                    summary="Differing DAR IDs reported by DSS instances in the same pool",
                    details=f"The following DSS instances reported different DAR IDs:\n{details}",
                )
