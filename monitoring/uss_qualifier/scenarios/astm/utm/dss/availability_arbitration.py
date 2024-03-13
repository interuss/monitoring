from uas_standards.astm.f3548.v21.api import ExchangeRecord
from uas_standards.astm.f3548.v21.constants import (
    Scope,
)

from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import make_report

from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    ScenarioCannotContinueError,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext

from monitoring.monitorlib.clients import scd as scd_client
from monitoring.monitorlib import scd as scd_lib


class AvailabilityArbitration(TestScenario):
    def __init__(
        self,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        scopes = {
            Scope.AvailabilityArbitration: "get/set USS availability and submit DSS reports"
        }
        self._dss = dss.get_instance(scopes)

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("DSS Report")
        self._dss_report_case()
        self.end_test_case()

        self.begin_test_case("USS Availability")
        self._uss_availability_case()
        self.end_test_case()

        self.end_test_scenario()

    def _dss_report_case(self):
        def gen_record() -> ExchangeRecord:
            try:
                op_intent, _ = scd_client.get_operational_intent_details(
                    self._dss.client, "http://dummy.interuss.org", "dummy_id"
                )
            except QueryError as qe:
                return scd_lib.make_exchange_record(
                    qe.queries[0], "this is a dummy record created by the USS qualifier"
                )

            # we are not supposed to reach this state
            raise ScenarioCannotContinueError(
                "illegal state: get_operational_intent_details to a dummy USS did not raise a QueryError"
            )

        self.begin_test_step("Make valid DSS report")
        dummy_record = gen_record()
        report_id = make_report(self, self._dss, dummy_record)
        self.record_note(f"{self._dss.participant_id}/report_id", report_id)
        self.end_test_step()

    def _uss_availability_case(self):
        # TODO: implement me
        pass
