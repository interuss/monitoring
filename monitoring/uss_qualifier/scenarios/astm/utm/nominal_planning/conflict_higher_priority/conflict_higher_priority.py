from typing import Optional, Tuple

import arrow

from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
)

from monitoring.monitorlib.geotemporal import Volume4DCollection
from uas_standards.astm.f3548.v21.api import OperationalIntentState
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
)

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
    activate_priority_conflict_flight_intent,
    plan_priority_conflict_flight_intent,
    modify_planned_priority_conflict_flight_intent,
    modify_activated_priority_conflict_flight_intent,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    plan_flight_intent,
    cleanup_flights,
    activate_flight_intent,
    delete_flight_intent,
    modify_activated_flight_intent,
)


class ConflictHigherPriority(TestScenario):
    flight1_id: Optional[str] = None
    flight1_planned: FlightIntent
    flight1m_planned: FlightIntent
    flight1_activated: FlightIntent
    flight1m_activated: FlightIntent
    flight1c_activated: FlightIntent

    flight2_id: Optional[str] = None
    flight2_planned: FlightIntent
    flight2_activated: FlightIntent
    flight2m_activated: FlightIntent

    tested_uss: FlightPlanner
    control_uss: FlightPlanner
    dss: DSSInstance

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        tested_uss: FlightPlannerResource,
        control_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        self.tested_uss = tested_uss.flight_planner
        self.control_uss = control_uss.flight_planner
        self.dss = dss.dss

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
                self.flight1_planned,
                self.flight1m_planned,
                self.flight1_activated,
                self.flight1m_activated,
                self.flight1c_activated,
                self.flight2_planned,
                self.flight2_activated,
                self.flight2m_activated,
            ) = (
                _flight_intents["flight1_planned"],
                _flight_intents["flight1m_planned"],
                _flight_intents["flight1_activated"],
                _flight_intents["flight1m_activated"],
                _flight_intents["flight1c_activated"],
                _flight_intents["flight2_planned"],
                _flight_intents["flight2_activated"],
                _flight_intents["flight2m_activated"],
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
                self.flight1_planned.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight1_planned must have state Accepted"
            assert (
                self.flight1m_planned.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight1m_planned must have state Accepted"
            assert (
                self.flight1_activated.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight1_activated must have state Activated"
            assert (
                self.flight1m_activated.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight1m_activated must have state Activated"
            assert (
                self.flight1c_activated.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight1c_activated must have state Activated"
            assert (
                self.flight2_planned.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight2_planned must have state Accepted"
            assert (
                self.flight2_activated.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight2_activated must have state Activated"
            assert (
                self.flight2m_activated.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight2m_activated must have state Activated"

            # TODO: check that flight data is the same across the different versions of the flight

            assert (
                self.flight2_planned.request.operational_intent.priority
                > self.flight1_planned.request.operational_intent.priority
            ), "flight_2 must have higher priority than flight_1"
            assert Volume4DCollection.from_interuss_scd_api(
                self.flight1_planned.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.flight2_planned.request.operational_intent.volumes
                )
            ), "flight1_planned and flight2_planned must intersect"
            assert Volume4DCollection.from_interuss_scd_api(
                self.flight1_planned.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.flight1m_planned.request.operational_intent.volumes
                )
            ), "flight1_planned and flight1m_planned must intersect"
            assert not Volume4DCollection.from_interuss_scd_api(
                self.flight1_planned.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.flight1c_activated.request.operational_intent.volumes
                )
            ), "flight1_planned and flight1c_activated must not intersect"

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

        self.begin_test_case("Attempt to plan flight in conflict")
        self._attempt_plan_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify planned flight in conflict")
        flight_1_oi_ref = self._attempt_modify_planned_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to activate flight in conflict")
        flight_1_oi_ref = self._attempt_activate_flight_conflict(flight_1_oi_ref)
        self.end_test_case()

        self.begin_test_case("Modify activated flight with pre-existing conflict")
        (
            flight_1_oi_ref,
            flight_2_oi_ref,
        ) = self._modify_activated_flight_conflict_preexisting(flight_1_oi_ref)
        self.end_test_case()

        self.begin_test_case("Attempt to modify activated flight in conflict")
        self._attempt_modify_activated_flight_conflict(flight_1_oi_ref, flight_2_oi_ref)
        self.end_test_case()

        self.end_test_scenario()

    def _attempt_plan_flight_conflict(self):
        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self._intents_extent,
        ) as validator:
            resp_flight_2, self.flight2_id = plan_flight_intent(
                self,
                "Plan flight 2",
                self.control_uss,
                self.flight2_planned.request,
            )
            validator.expect_shared(self.flight2_planned.request)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not shared",
            self._intents_extent,
        ) as validator:
            _ = plan_priority_conflict_flight_intent(
                self,
                "Attempt to plan flight 1",
                self.tested_uss,
                self.flight1_planned.request,
            )
            validator.expect_not_shared()

        _ = delete_flight_intent(
            self, "Delete flight 2", self.control_uss, self.flight2_id
        )
        self.flight2_id = None

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
            resp_flight_1, self.flight1_id = plan_flight_intent(
                self,
                "Plan flight 1",
                self.tested_uss,
                self.flight1_planned.request,
            )
            flight_1_oi_ref = validator.expect_shared(self.flight1_planned.request)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self._intents_extent,
        ) as validator:
            resp_flight_2, self.flight2_id = plan_flight_intent(
                self,
                "Plan flight 2",
                self.control_uss,
                self.flight2_planned.request,
            )
            validator.expect_shared(self.flight2_planned.request)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not modified",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            _ = modify_planned_priority_conflict_flight_intent(
                self,
                "Attempt to modify planned flight 1 in conflict",
                self.tested_uss,
                self.flight1m_planned.request,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                self.flight1_planned.request, skip_if_not_found=True
            )

        return flight_1_oi_ref

    def _attempt_activate_flight_conflict(
        self, flight_1_oi_ref: Optional[OperationalIntentReference]
    ) -> Optional[OperationalIntentReference]:
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not activated",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            _ = activate_priority_conflict_flight_intent(
                self,
                "Attempt to activate conflicting flight 1",
                self.tested_uss,
                self.flight1_activated.request,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                self.flight1_planned.request, skip_if_not_found=True
            )

        return flight_1_oi_ref

    def _modify_activated_flight_conflict_preexisting(
        self, flight_1_oi_ref: Optional[OperationalIntentReference]
    ) -> Tuple[OperationalIntentReference, OperationalIntentReference]:
        _ = delete_flight_intent(
            self, "Delete flight 2", self.control_uss, self.flight2_id
        )
        self.flight2_id = None

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
                self.flight1_activated.request,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(self.flight1_activated.request)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self._intents_extent,
        ) as validator:
            _, self.flight2_id = plan_flight_intent(
                self,
                "Plan flight 2",
                self.control_uss,
                self.flight2_planned.request,
            )
            flight_2_oi_ref = validator.expect_shared(self.flight2_planned.request)

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
                self.flight2_activated.request,
                self.flight2_id,
            )
            flight_2_oi_ref = validator.expect_shared(self.flight2_activated.request)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 sharing",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            resp = modify_activated_flight_intent(
                self,
                "Modify activated flight 1 in conflict with activated flight 2",
                self.tested_uss,
                self.flight1m_activated.request,
                self.flight1_id,
                preexisting_conflict=True,
            )

            if resp.result == InjectFlightResponseResult.ReadyToFly:
                flight_1_oi_ref = validator.expect_shared(
                    self.flight1m_activated.request
                )
            else:
                flight_1_oi_ref = validator.expect_shared(
                    self.flight1_activated.request
                )

        return flight_1_oi_ref, flight_2_oi_ref

    def _attempt_modify_activated_flight_conflict(
        self,
        flight_1_oi_ref: OperationalIntentReference,
        flight_2_oi_ref: OperationalIntentReference,
    ):
        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self._intents_extent,
            flight_2_oi_ref,
        ) as validator:
            modify_activated_flight_intent(
                self,
                "Modify activated flight 2 to not conflict with activated flight 1",
                self.control_uss,
                self.flight2m_activated.request,
                self.flight2_id,
            )
            validator.expect_shared(self.flight2m_activated.request)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not modified",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            modify_activated_priority_conflict_flight_intent(
                self,
                "Attempt to modify activated flight 1 in conflict",
                self.tested_uss,
                self.flight1c_activated.request,
                self.flight1_id,
            )
            validator.expect_shared(
                self.flight1m_activated.request,
                skip_if_not_found=True,
            )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.control_uss, self.tested_uss))
        self.end_cleanup()
