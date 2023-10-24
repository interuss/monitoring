from datetime import datetime
from typing import Optional, List, Callable

import arrow
from uas_standards.astm.f3548.v21 import api as f3548_v21
from uas_standards.astm.f3548.v21.constants import OiMaxVertices, OiMaxPlanHorizonDays
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_api

from monitoring.mock_uss.scdsc.database import FlightRecord
from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.monitorlib.locality import Locality
from monitoring.monitorlib.uspace import problems_with_flight_authorisation
from uas_standards.interuss.automated_testing.scd.v1.api import OperationalIntentState


class PlanningError(Exception):
    pass


def validate_request(req_body: scd_api.InjectFlightRequest, locality: Locality) -> None:
    """Raise a PlannerError if the request is not valid.

    Args:
        req_body: Information about the requested flight.
        locality: Jurisdictional requirements which the mock_uss should follow.
    """
    if locality.is_uspace_applicable():
        # Validate flight authorisation
        problems = problems_with_flight_authorisation(req_body.flight_authorisation)
        if problems:
            raise PlanningError(", ".join(problems))

    # Validate max number of vertices
    nb_vertices = 0
    for volume in (
        req_body.operational_intent.volumes
        + req_body.operational_intent.off_nominal_volumes
    ):
        if volume.volume.has_field_with_value("outline_polygon"):
            nb_vertices += len(volume.volume.outline_polygon.vertices)
        if volume.volume.has_field_with_value("outline_circle"):
            nb_vertices += 1

    if nb_vertices > OiMaxVertices:
        raise PlanningError(
            f"Too many vertices across volumes of operational intent (max OiMaxVertices={OiMaxVertices})"
        )

    # Validate max planning horizon for creation
    start_time = Volume4DCollection.from_interuss_scd_api(
        req_body.operational_intent.volumes
        + req_body.operational_intent.off_nominal_volumes
    ).time_start.datetime
    time_delta = start_time - datetime.now(tz=start_time.tzinfo)
    if (
        time_delta.days > OiMaxPlanHorizonDays
        and req_body.operational_intent.state == scd_api.OperationalIntentState.Accepted
    ):
        raise PlanningError(
            f"Operational intent to plan is too far away in time (max OiMaxPlanHorizonDays={OiMaxPlanHorizonDays})"
        )

    # Validate no off_nominal_volumes if in Accepted or Activated state
    if len(req_body.operational_intent.off_nominal_volumes) > 0 and (
        req_body.operational_intent.state == scd_api.OperationalIntentState.Accepted
        or req_body.operational_intent.state == scd_api.OperationalIntentState.Activated
    ):
        raise PlanningError(
            f"Operational intent specifies an off-nominal volume while being in {req_body.operational_intent.state} state"
        )

    # Validate intent is currently active if in Activated state
    # I.e. at least one volume has start time in the past and end time in the future
    if req_body.operational_intent.state == OperationalIntentState.Activated:
        now = arrow.utcnow().datetime
        active_volume = Volume4DCollection.from_interuss_scd_api(
            req_body.operational_intent.volumes
            + req_body.operational_intent.off_nominal_volumes
        ).has_active_volume(now)
        if not active_volume:
            raise PlanningError(
                f"Operational intent is activated but has no volume currently active (now: {now})"
            )


def check_for_disallowed_conflicts(
    req_body: scd_api.InjectFlightRequest,
    existing_flight: Optional[FlightRecord],
    op_intents: List[f3548_v21.OperationalIntent],
    locality: Locality,
    log: Optional[Callable[[str], None]] = None,
) -> None:
    """Raise a PlannerError if there are any disallowed conflicts.

    Args:
        req_body: Information about the requested flight.
        existing_flight: The existing state of the flight (to be changed by the request), or None if this request is to
            create a new flight.
        op_intents: Full information for all potentially-relevant operational intents.
        locality: Jurisdictional requirements which the mock_uss should follow.
        log: If specified, call this function to report information about conflict evaluation.
    """
    if log is None:
        log = lambda msg: None

    if req_body.operational_intent.state not in (
        OperationalIntentState.Accepted,
        OperationalIntentState.Activated,
    ):
        # No conflicts are disallowed if the flight is not nominal
        return

    v1 = Volume4DCollection.from_interuss_scd_api(req_body.operational_intent.volumes)

    for op_intent in op_intents:
        if (
            existing_flight
            and existing_flight.op_intent.reference.id == op_intent.reference.id
        ):
            log(
                f"intersection with {op_intent.reference.id} not considered: intersection with a past version of this flight"
            )
            continue
        if req_body.operational_intent.priority > op_intent.details.priority:
            log(
                f"intersection with {op_intent.reference.id} not considered: intersection with lower-priority operational intents"
            )
            continue
        if (
            req_body.operational_intent.priority == op_intent.details.priority
            and locality.allows_same_priority_intersections(
                req_body.operational_intent.priority
            )
        ):
            log(
                f"intersection with {op_intent.reference.id} not considered: intersection with same-priority operational intents (if allowed)"
            )
            continue

        v2 = Volume4DCollection.from_interuss_scd_api(
            op_intent.details.volumes + op_intent.details.off_nominal_volumes
        )

        modifying_activated = (
            existing_flight
            and existing_flight.op_intent.reference.state
            == scd_api.OperationalIntentState.Activated
            and req_body.operational_intent.state
            == scd_api.OperationalIntentState.Activated
        )
        if modifying_activated:
            preexisting_conflict = Volume4DCollection.from_interuss_scd_api(
                existing_flight.op_intent.details.volumes
            ).intersects_vol4s(v2)
            if preexisting_conflict:
                log(
                    f"intersection with {op_intent.reference.id} not considered: modification of Activated operational intent with a pre-existing conflict"
                )
                continue

        if v1.intersects_vol4s(v2):
            raise PlanningError(
                f"Requested flight (priority {req_body.operational_intent.priority}) intersected {op_intent.reference.manager}'s operational intent {op_intent.reference.id} (priority {op_intent.details.priority})"
            )


def op_intent_transition_valid(
    transition_from: Optional[scd_api.OperationalIntentState],
    transition_to: Optional[scd_api.OperationalIntentState],
) -> bool:
    valid_states = {
        scd_api.OperationalIntentState.Accepted,
        scd_api.OperationalIntentState.Activated,
        scd_api.OperationalIntentState.Nonconforming,
        scd_api.OperationalIntentState.Contingent,
    }
    if transition_from is not None and transition_from not in valid_states:
        raise ValueError(
            f"Cannot transition from state {transition_from} as it is an invalid operational intent state"
        )
    if transition_to is not None and transition_to not in valid_states:
        raise ValueError(
            f"Cannot transition to state {transition_to} as it is an invalid operational intent state"
        )

    if transition_from is None:
        return transition_to in {
            scd_api.OperationalIntentState.Accepted,
            scd_api.OperationalIntentState.Activated,
        }

    elif transition_from == scd_api.OperationalIntentState.Accepted:
        return transition_to in {
            None,
            scd_api.OperationalIntentState.Accepted,
            scd_api.OperationalIntentState.Activated,
            scd_api.OperationalIntentState.Nonconforming,
            scd_api.OperationalIntentState.Contingent,
        }

    elif transition_from == scd_api.OperationalIntentState.Activated:
        return transition_to in {
            None,
            scd_api.OperationalIntentState.Activated,
            scd_api.OperationalIntentState.Nonconforming,
            scd_api.OperationalIntentState.Contingent,
        }

    elif transition_from == scd_api.OperationalIntentState.Nonconforming:
        return transition_to in {
            None,
            scd_api.OperationalIntentState.Nonconforming,
            scd_api.OperationalIntentState.Activated,
            scd_api.OperationalIntentState.Contingent,
        }

    elif transition_from == scd_api.OperationalIntentState.Contingent:
        return transition_to in {None, scd_api.OperationalIntentState.Contingent}

    else:
        return False
