from typing import Optional, List

from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightPlannersResource,
    FlightIntentsResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.test_step_fragments import (
    remove_op_intent,
)
from monitoring.uss_qualifier.scenarios.flight_planning.prep_planners import (
    PrepareFlightPlanners as GenericPrepareFlightPlanners,
)
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSResource,
)
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
)
from uas_standards.astm.f3548.v21.constants import Scope


class PrepareFlightPlanners(GenericPrepareFlightPlanners):
    dss: DSSInstance

    def __init__(
        self,
        flight_planners: FlightPlannersResource,
        dss: DSSInstanceResource,
        flight_intents: FlightIntentsResource,
        mock_uss: Optional[MockUSSResource] = None,
        flight_intents2: Optional[FlightIntentsResource] = None,
        flight_intents3: Optional[FlightIntentsResource] = None,
        flight_intents4: Optional[FlightIntentsResource] = None,
    ):
        super(PrepareFlightPlanners, self).__init__(
            flight_planners,
            flight_intents,
            mock_uss,
            flight_intents2,
            flight_intents3,
            flight_intents4,
        )
        self.dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "search for operational intent references and remove ones under uss_qualifier management"
            }
        )

    def run(self, context):
        self.begin_test_scenario(context)

        self.begin_test_case("Flight planners preparation")

        self.begin_test_step("Check for flight planning readiness")
        self._check_readiness()
        self.end_test_step()

        self.begin_test_step("Area clearing")
        self._clear_area()
        self.end_test_step()

        self.begin_test_step("Clear area validation")
        remaining_op_intents = self._validate_clear_area(
            "Area is clear of foreign op intents", ignore_self=True
        )
        self.end_test_step()

        self.end_test_case()

        if remaining_op_intents:
            self.begin_test_case("uss_qualifier preparation")

            self.begin_test_step("Remove uss_qualifier op intents")
            self._remove_my_op_intents(remaining_op_intents)
            self.end_test_step()

            self.begin_test_step("Clear area validation")
            self._validate_clear_area("Area is clear", ignore_self=False)
            self.end_test_step()

            self.end_test_case()

        self.end_test_scenario()

    def _validate_clear_area(
        self, check_name: str, ignore_self: bool
    ) -> List[OperationalIntentReference]:
        found_intents = []
        for area in self.areas:
            with self.check("DSS responses", [self.dss.participant_id]) as check:
                try:
                    op_intents, query = self.dss.find_op_intent(area.to_f3548v21())
                except ValueError as e:
                    check.record_failed(
                        summary="Error parsing DSS response",
                        details=str(e),
                    )
                self.record_query(query)
                if op_intents is None:
                    check.record_failed(
                        summary="Error querying DSS for operational intents",
                        details="See query",
                        query_timestamps=[query.request.timestamp],
                    )
            found_intents.extend(op_intents)

            with self.check(check_name) as check:
                if ignore_self:
                    uss_qualifier_sub = self.dss.client.auth_adapter.get_sub()
                    op_intents = [
                        oi for oi in op_intents if oi.manager != uss_qualifier_sub
                    ]
                if op_intents:
                    summary = f"{len(op_intents)} operational intent{'s' if len(op_intents) > 1 else ''} found in cleared area"
                    details = (
                        "The following operational intents were observed even after clearing the area:\n"
                        + "\n".join(
                            f"* {oi.id} managed by {oi.manager}" for oi in op_intents
                        )
                    )
                    check.record_failed(
                        summary=summary,
                        details=details,
                        query_timestamps=[query.request.timestamp],
                    )

        return found_intents

    def _remove_my_op_intents(
        self, my_op_intents: List[OperationalIntentReference]
    ) -> None:
        already_removed = set()
        for oi_ref in my_op_intents:
            if oi_ref.id in already_removed:
                continue
            remove_op_intent(self, self.dss, oi_ref.id, oi_ref.ovn)
            already_removed.add(oi_ref.id)
