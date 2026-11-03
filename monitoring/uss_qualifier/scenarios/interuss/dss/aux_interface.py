from monitoring.monitorlib.clients.interuss.dss import InterUSSDSSClient
from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class AuxInterface(TestScenario):
    def __init__(self, dss: DSSInstanceResource):
        super().__init__()
        self._dss = dss.get_instance({})
        self._pid = [self._dss.participant_id]
        self._client = InterUSSDSSClient(
            session=self._dss.client, participant_id=self._dss.participant_id
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Version")
        self.begin_test_step("Query version")
        self._query_version()
        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()

    def _query_version(self):
        with self.check("Version can be queried", self._pid) as check:
            try:
                resp, query = self._client.get_version()
                self.record_query(query)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="Failed to query DSS version",
                    details=e.msg,
                    query_timestamps=e.query_timestamps,
                )
                return

        with self.check("Version is defined", self._pid) as check:
            if not resp.version or "undefined" in resp.version:
                check.record_failed(
                    summary="DSS version is not defined",
                    details=f"DSS reported version `{resp.version}`",
                    query_timestamps=[query.request.timestamp],
                )
