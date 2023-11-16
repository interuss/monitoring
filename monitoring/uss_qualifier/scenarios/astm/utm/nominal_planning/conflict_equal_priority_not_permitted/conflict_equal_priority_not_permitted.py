from typing import Optional

import arrow

from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
)
from monitoring.monitorlib.geotemporal import Volume4DCollection
from uas_standards.astm.f3548.v21.api import OperationalIntentState

from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntent,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlanner,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidator,
)
from monitoring.uss_qualifier.scenarios.flight_planning.prioritization_test_steps import (
    modify_planned_conflict_flight_intent,
    modify_activated_conflict_flight_intent,
    activate_conflict_flight_intent,
    plan_conflict_flight_intent,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    ScenarioCannotContinueError,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    plan_flight_intent,
    cleanup_flights,
    activate_flight_intent,
    submit_flight_intent,
)
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
)


class ConflictEqualPriorityNotPermitted(TestScenario):
    flight_1_id: Optional[str] = None
    flight_1_planned_vol_A: FlightIntent
    flight_1_activated_vol_A: FlightIntent
    flight_1_activated_vol_A_extended: FlightIntent
    flight_1_planned_vol_B: FlightIntent
    flight_1_activated_vol_B: FlightIntent

    flight_2_id: Optional[str] = None
    flight_2_equal_prio_planned_vol_B: FlightIntent
    flight_2_equal_prio_activated_vol_B: FlightIntent
    flight_2_equal_prio_nonconforming_vol_A: FlightIntent

    tested_uss: FlightPlanner
    control_uss: FlightPlanner
    dss: DSSInstance

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        control_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
        flight_intents: Optional[FlightIntentsResource] = None,
    ):
        super().__init__()
        self.tested_uss = tested_uss.flight_planner
        self.control_uss = control_uss.flight_planner
        self.dss = dss.dss

        if not flight_intents:
            msg = f"No FlightIntentsResource was provided as input to this test, it is assumed that the jurisdiction of the tested USS ({self.tested_uss.config.participant_id}) does not allow any same priority conflicts, execution of the scenario was stopped without failure"
            self.record_note(
                "Jurisdiction of tested USS does not allow any same priority conflicts",
                msg,
            )
            raise ScenarioCannotContinueError(msg)

        _flight_intents = {
            k: FlightIntent.from_flight_info_template(v)
            for k, v in flight_intents.get_flight_intents().items()
        }

        extents = []
        for intent in _flight_intents.values():
            extents.extend(intent.request.operational_intent.volumes)
            extents.extend(intent.request.operational_intent.off_nominal_volumes)
        self._intents_extent = Volume4DCollection.from_interuss_scd_api(
            extents
        ).bounding_volume.to_f3548v21()

        try:
            (
                self.flight_1_planned_vol_A,
                self.flight_1_activated_vol_A,
                self.flight_1_activated_vol_A_extended,
                self.flight_1_planned_vol_B,
                self.flight_1_activated_vol_B,
                self.flight_2_equal_prio_planned_vol_B,
                self.flight_2_equal_prio_activated_vol_B,
                self.flight_2_equal_prio_nonconforming_vol_A,
            ) = (
                _flight_intents["flight_1_planned_vol_A"],
                _flight_intents["flight_1_activated_vol_A"],
                _flight_intents["flight_1_activated_vol_A_extended"],
                _flight_intents["flight_1_planned_vol_B"],
                _flight_intents["flight_1_activated_vol_B"],
                _flight_intents["flight_2_equal_prio_planned_vol_B"],
                _flight_intents["flight_2_equal_prio_activated_vol_B"],
                _flight_intents["flight_2_equal_prio_nonconforming_vol_A"],
            )

            now = arrow.utcnow().datetime
            for intent_name, intent in _flight_intents.items():
                if (
                    intent.request.operational_intent.state
                    == OperationalIntentState.Activated
                ):
                    assert Volume4DCollection.from_interuss_scd_api(
                        intent.request.operational_intent.volumes
                        + intent.request.operational_intent.off_nominal_volumes
                    ).has_active_volume(
                        now
                    ), f"at least one volume of activated intent {intent_name} must be active now (now is {now})"

            assert (
                self.flight_1_planned_vol_A.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_1_planned_vol_A must have state Accepted"
            assert (
                self.flight_1_activated_vol_A.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_1_activated_vol_A must have state Activated"
            assert (
                self.flight_1_activated_vol_A_extended.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_1_activated_vol_A_extended must have state Activated"
            assert (
                self.flight_1_planned_vol_B.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_1_planned_vol_B must have state Accepted"
            assert (
                self.flight_1_activated_vol_B.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_1_activated_vol_B must have state Activated"
            assert (
                self.flight_2_equal_prio_planned_vol_B.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_2_equal_prio_planned_vol_B must have state Accepted"
            assert (
                self.flight_2_equal_prio_activated_vol_B.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_2_equal_prio_activated_vol_B must have state Activated"
            assert (
                self.flight_2_equal_prio_nonconforming_vol_A.request.operational_intent.state
                == OperationalIntentState.Nonconforming
            ), "flight_2_equal_prio_nonconforming_vol_A must have state Nonconforming"

            assert (
                self.flight_2_equal_prio_planned_vol_B.request.operational_intent.priority
                == self.flight_1_planned_vol_A.request.operational_intent.priority
            ), "flight_2 must have priority equal to flight_1"
            assert not Volume4DCollection.from_interuss_scd_api(
                self.flight_1_planned_vol_A.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.flight_2_equal_prio_planned_vol_B.request.operational_intent.volumes
                )
            ), "flight_1_planned_vol_A and flight_2_equal_prio_planned_vol_B must not intersect"
            assert not Volume4DCollection.from_interuss_scd_api(
                self.flight_1_planned_vol_A.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.flight_1_activated_vol_B.request.operational_intent.volumes
                )
            ), "flight_1_planned_vol_A and flight_1_activated_vol_B must not intersect"
            assert Volume4DCollection.from_interuss_scd_api(
                self.flight_1_activated_vol_B.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.flight_2_equal_prio_activated_vol_B.request.operational_intent.volumes
                )
            ), "flight_1_activated_vol_B and flight_2_equal_prio_activated_vol_B must intersect"
            assert Volume4DCollection.from_interuss_scd_api(
                self.flight_1_activated_vol_A.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.flight_2_equal_prio_nonconforming_vol_A.request.operational_intent.off_nominal_volumes
                )
            ), "flight_1_activated_vol_A.volumes and flight_2_equal_prio_nonconforming_vol_A.off_nominal_volumes must intersect"

            assert (
                len(
                    self.flight_2_equal_prio_nonconforming_vol_A.request.operational_intent.off_nominal_volumes
                )
                > 0
            ), "flight_2_equal_prio_nonconforming_vol_A must have off-nominal volume"

        except KeyError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: missing flight intent {e}"
            )
        except AssertionError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.record_note(
            "Tested USS",
            f"{self.tested_uss.config.participant_id}",
        )
        self.record_note(
            "Control USS",
            f"{self.control_uss.config.participant_id}",
        )

        self.begin_test_case("Attempt to plan flight into conflict")
        flight_2_oi_ref = self._attempt_plan_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to activate flight into conflict")
        self._attempt_activate_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify planned flight into conflict")
        flight_1_oi_ref = self._attempt_modify_planned_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify activated flight into conflict")
        flight_1_oi_ref = self._attempt_modify_activated_flight_conflict(
            flight_1_oi_ref
        )
        self.end_test_case()

        self.begin_test_case("Modify activated flight with pre-existing conflict")
        self._modify_activated_flight_preexisting_conflict(
            flight_1_oi_ref, flight_2_oi_ref
        )
        self.end_test_case()

        self.end_test_scenario()

    def _attempt_plan_flight_conflict(self) -> OperationalIntentReference:
        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self._intents_extent,
        ) as validator:
            _, self.flight_2_id = plan_flight_intent(
                self,
                "Plan flight 2",
                self.control_uss,
                self.flight_2_equal_prio_planned_vol_B.request,
            )
            flight_2_oi_ref = validator.expect_shared(
                self.flight_2_equal_prio_planned_vol_B.request
            )

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self._intents_extent,
            flight_2_oi_ref,
        ) as validator:
            activate_flight_intent(
                self,
                "Activate flight 2",
                self.control_uss,
                self.flight_2_equal_prio_activated_vol_B.request,
                self.flight_2_id,
            )
            flight_2_oi_ref = validator.expect_shared(
                self.flight_2_equal_prio_activated_vol_B.request
            )

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not shared",
            self._intents_extent,
        ) as validator:
            plan_conflict_flight_intent(
                self,
                "Attempt to plan flight 1",
                self.tested_uss,
                self.flight_1_planned_vol_B.request,
            )
            validator.expect_not_shared()

        return flight_2_oi_ref

    def _attempt_activate_flight_conflict(self):
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not shared",
            self._intents_extent,
        ) as validator:
            activate_conflict_flight_intent(
                self,
                "Attempt to directly activate conflicting flight 1",
                self.tested_uss,
                self.flight_1_activated_vol_B.request,
                self.flight_1_id,
            )
            validator.expect_not_shared()

    def _attempt_modify_planned_flight_conflict(
        self,
    ) -> Optional[OperationalIntentReference]:
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 sharing",
            self._intents_extent,
        ) as validator:
            _, self.flight_1_id = plan_flight_intent(
                self,
                "Plan flight 1",
                self.tested_uss,
                self.flight_1_planned_vol_A.request,
            )
            flight_1_oi_ref = validator.expect_shared(
                self.flight_1_planned_vol_A.request
            )

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not modified",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            modify_planned_conflict_flight_intent(
                self,
                "Attempt to modify planned flight 1 into conflict",
                self.tested_uss,
                self.flight_1_planned_vol_B.request,
                self.flight_1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                self.flight_1_planned_vol_A.request, skip_if_not_found=True
            )

        return flight_1_oi_ref

    def _attempt_modify_activated_flight_conflict(
        self, flight_1_oi_ref: Optional[OperationalIntentReference]
    ) -> Optional[OperationalIntentReference]:
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 sharing",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            activate_flight_intent(
                self,
                "Activate flight 1",
                self.tested_uss,
                self.flight_1_activated_vol_A.request,
                self.flight_1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                self.flight_1_activated_vol_A.request
            )

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not modified",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            modify_activated_conflict_flight_intent(
                self,
                "Attempt to modify activated flight 1 into conflict",
                self.tested_uss,
                self.flight_1_activated_vol_B.request,
                self.flight_1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                self.flight_1_activated_vol_A.request, skip_if_not_found=True
            )

        return flight_1_oi_ref

    def _modify_activated_flight_preexisting_conflict(
        self,
        flight_1_oi_ref: Optional[OperationalIntentReference],
        flight_2_oi_ref: Optional[OperationalIntentReference],
    ):
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 sharing",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            activate_flight_intent(
                self,
                "Activate flight 1",
                self.tested_uss,
                self.flight_1_activated_vol_A.request,
                self.flight_1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                self.flight_1_activated_vol_A.request
            )

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self._intents_extent,
            flight_2_oi_ref,
        ) as validator:
            resp_flight_2, _ = submit_flight_intent(
                self,
                "Declare flight 2 non-conforming",
                "Successful transition to non-conforming state",
                {
                    InjectFlightResponseResult.ReadyToFly,
                    InjectFlightResponseResult.NotSupported,
                },
                {InjectFlightResponseResult.Failed: "Failure"},
                self.control_uss,
                self.flight_2_equal_prio_nonconforming_vol_A.request,
                self.flight_2_id,
            )
            if resp_flight_2.result == InjectFlightResponseResult.NotSupported:
                msg = f"{self.control_uss.config.participant_id} does not support the transition to a Nonconforming state; execution of the scenario was stopped without failure"
                self.record_note("Control USS does not support CMSA role", msg)
                raise ScenarioCannotContinueError(msg)

            validator.expect_shared(
                self.flight_2_equal_prio_nonconforming_vol_A.request
            )

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            resp_flight_1, _ = submit_flight_intent(
                self,
                "Attempt to modify activated flight 1 in conflict with nonconforming flight 2",
                "Successful modification or rejection",
                {
                    InjectFlightResponseResult.ReadyToFly,
                    InjectFlightResponseResult.Rejected,
                },
                {InjectFlightResponseResult.Failed: "Failure"},
                self.tested_uss,
                self.flight_1_activated_vol_A_extended.request,
                self.flight_1_id,
            )

            if resp_flight_1.result == InjectFlightResponseResult.ReadyToFly:
                validator.expect_shared(self.flight_1_activated_vol_A_extended.request)
            elif resp_flight_1.result == InjectFlightResponseResult.Rejected:
                validator.expect_shared(
                    self.flight_1_activated_vol_A.request, skip_if_not_found=True
                )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.control_uss, self.tested_uss))
        self.end_cleanup()
