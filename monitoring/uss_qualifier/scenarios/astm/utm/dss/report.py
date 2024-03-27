from uas_standards.astm.f3548.v21.api import ExchangeRecord, OPERATIONS, OperationID
from uas_standards.astm.f3548.v21.constants import (
    Scope,
)

from monitoring.monitorlib.fetch import QueryError, query_and_describe, QueryType
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import make_dss_report

from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    ScenarioCannotContinueError,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext

from monitoring.monitorlib import scd as scd_lib, infrastructure


class Report(TestScenario):
    def __init__(
        self,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        scopes = {
            Scope.StrategicCoordination: "get operational intent reference and submit a DSS report"
        }
        self._dss = dss.get_instance(scopes)

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("DSS Report")
        self._dss_report_case()
        self.end_test_case()

        self.end_test_scenario()

    def _dss_report_case(self):
        def gen_record() -> ExchangeRecord:
            op = OPERATIONS[OperationID.GetOperationalIntentReference]
            query = query_and_describe(
                infrastructure.UTMClientSession("https://dummy.interuss.org"),
                op.verb,
                op.path.format(entityid="dummy_op_intent_id"),
                QueryType.F3548v21DSSGetOperationalIntentReference,
                "dummy_dss",
                True,
            )
            if not query.response.code:
                return scd_lib.make_exchange_record(
                    query,
                    "this is a dummy record created by the USS qualifier. This failure is expected.",
                )

            # we are not supposed to reach this state
            raise RuntimeError(
                "illegal state: getOperationalIntentReference to a dummy DSS shall not have succeeded"
            )

        self.begin_test_step("Make valid DSS report")
        dummy_record = gen_record()
        report_id = make_dss_report(self, self._dss, dummy_record)
        self.record_note(f"{self._dss.participant_id}/report_id", report_id)
        self.end_test_step()
