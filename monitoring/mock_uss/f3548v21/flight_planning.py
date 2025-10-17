import uuid
from collections.abc import Callable
from datetime import datetime

import arrow
import requests
from uas_standards.astm.f3548.v21 import api as f3548_v21
from uas_standards.astm.f3548.v21.constants import OiMaxPlanHorizonDays, OiMaxVertices
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_api

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.config import KEY_BASE_URL
from monitoring.mock_uss.f3548v21 import utm_client
from monitoring.mock_uss.flights.database import FlightRecord, db
from monitoring.monitorlib.clients import scd as scd_client
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geo import Altitude, AltitudeDatum, DistanceUnits, Volume3D
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from monitoring.monitorlib.locality import Locality
from monitoring.monitorlib.scd import priority_of
from monitoring.uss_qualifier.resources.overrides import apply_overrides


class PlanningError(Exception):
    pass


def validate_request(op_intent: f3548_v21.OperationalIntent) -> None:
    """Raise a PlannerError if the request is not valid.

    Args:
        op_intent: Information about the requested flight.
    """
    # Validate max number of vertices
    nb_vertices = 0
    for volume in op_intent.details.volumes + op_intent.details.off_nominal_volumes:
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
        op_intent.details.volumes + op_intent.details.off_nominal_volumes
    ).time_start.datetime
    time_delta = start_time - datetime.now(tz=start_time.tzinfo)
    if (
        time_delta.days > OiMaxPlanHorizonDays
        and op_intent.reference.state == scd_api.OperationalIntentState.Accepted
    ):
        raise PlanningError(
            f"Operational intent to plan is too far away in time (max OiMaxPlanHorizonDays={OiMaxPlanHorizonDays})"
        )

    # Validate no off_nominal_volumes if in Accepted or Activated state
    if len(op_intent.details.off_nominal_volumes) > 0 and (
        op_intent.reference.state == scd_api.OperationalIntentState.Accepted
        or op_intent.reference.state == scd_api.OperationalIntentState.Activated
    ):
        raise PlanningError(
            f"Operational intent specifies an off-nominal volume while being in {op_intent.reference.state} state"
        )

    # Validate intent is currently active if in Activated state
    # I.e. at least one volume has start time in the past and end time in the future
    if op_intent.reference.state == scd_api.OperationalIntentState.Activated:
        now = arrow.utcnow().datetime
        active_volume = Volume4DCollection.from_interuss_scd_api(
            op_intent.details.volumes + op_intent.details.off_nominal_volumes
        ).has_active_volume(now)
        if not active_volume:
            raise PlanningError(
                f"Operational intent is activated but has no volume currently active (now: {now})"
            )

    # Validate intent is not (entirely) in the past
    now = arrow.utcnow().datetime
    volumes = Volume4DCollection.from_interuss_scd_api(
        op_intent.details.volumes + op_intent.details.off_nominal_volumes
    )
    if volumes.time_end.datetime < now:
        raise PlanningError(
            f"Operational intent is in the past (time_end: {volumes.time_end.datetime}; now: {now})"
        )


def conflicts_with_flightrecords(
    op_intent: f3548_v21.OperationalIntent, flights: list[FlightRecord | None]
) -> bool:
    """
    Return true if the OperationalIntent conflicts with (intersects) any of the specified FlightRecords that do not
    correspond with op_intent.
    """

    vc1 = Volume4DCollection.from_f3548v21(
        (op_intent.details.volumes or [])
        + (op_intent.details.off_nominal_volumes or [])
    )

    for other_flight in flights:
        if not other_flight:
            continue

        if other_flight.op_intent.reference.id == op_intent.reference.id:  # Same flight
            continue

        vc2 = Volume4DCollection.from_f3548v21(
            (other_flight.op_intent.details.volumes or [])
            + (other_flight.op_intent.details.off_nominal_volumes or [])
        )

        if vc1.intersects_vol4s(vc2):
            return True

    return False


def check_for_conflicts(
    new_op_intent: f3548_v21.OperationalIntent,
    existing_flight: FlightRecord | None,
    op_intents: list[f3548_v21.OperationalIntent],
    locality: Locality,
    log: Callable[[str], None] | None = None,
) -> bool:
    """Raise a PlannerError if there are any disallowed conflicts.
       Return a boolean, set to True if there are allowed conflicts.

    Args:
        new_op_intent: The prospective operational intent.
        existing_flight: The existing state of the flight (to be changed by the request), or None if this request is to
            create a new flight.
        op_intents: Full information for all potentially-relevant operational intents.
        locality: Jurisdictional requirements which the mock_uss should follow.
        log: If specified, call this function to report information about conflict evaluation.
    """
    if log is None:

        def log(msg):
            return None

    if new_op_intent.reference.state not in (
        scd_api.OperationalIntentState.Accepted,
        scd_api.OperationalIntentState.Activated,
    ):
        # No conflicts are disallowed if the flight is not nominal
        return False

    v1 = Volume4DCollection.from_interuss_scd_api(new_op_intent.details.volumes)

    allowed_conflict = False

    for op_intent in op_intents:
        if (
            existing_flight
            and existing_flight.op_intent.reference.id == op_intent.reference.id
        ):
            log(
                f"intersection with {op_intent.reference.id} not considered: intersection with a past version of this flight"
            )
            continue

        v2 = Volume4DCollection.from_interuss_scd_api(
            op_intent.details.volumes + op_intent.details.off_nominal_volumes
        )

        new_priority = priority_of(new_op_intent.details)
        old_priority = priority_of(op_intent.details)
        if new_priority > old_priority:
            log(
                f"intersection with {op_intent.reference.id} allowed: intersection with lower-priority operational intents"
            )

            allowed_conflict |= v1.intersects_vol4s(v2)
            continue
        if new_priority == old_priority and locality.allows_same_priority_intersections(
            old_priority
        ):
            log(
                f"intersection with {op_intent.reference.id} allowed: intersection with same-priority operational intents (if allowed)"
            )
            allowed_conflict |= v1.intersects_vol4s(v2)
            continue

        modifying_activated = (
            existing_flight
            and existing_flight.op_intent.reference.state
            == scd_api.OperationalIntentState.Activated
            and op_intent.reference.state == scd_api.OperationalIntentState.Activated
        )
        if modifying_activated:
            preexisting_conflict = Volume4DCollection.from_interuss_scd_api(
                existing_flight.op_intent.details.volumes
            ).intersects_vol4s(v2)
            if preexisting_conflict:
                log(
                    f"intersection with {op_intent.reference.id} allowed: modification of Activated operational intent with a pre-existing conflict"
                )
                continue

        if v1.intersects_vol4s(v2):
            raise PlanningError(
                f"Requested flight (priority {new_priority}) intersected {op_intent.reference.manager}'s operational intent {op_intent.reference.id} (priority {old_priority})"
            )

    return allowed_conflict


def op_intent_transition_valid(
    transition_from: scd_api.OperationalIntentState | None,
    transition_to: scd_api.OperationalIntentState | None,
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


def _convert_altitudes(volumes: Volume4DCollection) -> Volume4DCollection:
    """F3548-21 does not accept AGL altitudes; "convert" any AGL altitudes to WGS84-HAE assuming an arbitrary ground elevation."""
    GROUND_ELEVATION = 123  # meters WGS84-HAE
    # TODO: Use better estimate for ground elevation
    result = []
    for v in volumes:
        convert = False
        if (
            v.volume.altitude_lower
            and v.volume.altitude_lower.reference != AltitudeDatum.W84
        ):
            convert = True
        if (
            v.volume.altitude_upper
            and v.volume.altitude_upper.reference != AltitudeDatum.W84
        ):
            convert = True
        if convert:
            kwargs = {}
            if "outline_polygon" in v.volume:
                kwargs["outline_polygon"] = v.volume.outline_polygon
            if "outline_circle" in v.volume:
                kwargs["outline_circle"] = v.volume.outline_circle
            if v.volume.altitude_lower:
                if v.volume.altitude_lower.reference == AltitudeDatum.W84:
                    kwargs["altitude_lower"] = v.volume.altitude_lower
                elif v.volume.altitude_lower.reference == AltitudeDatum.SFC:
                    if v.volume.altitude_lower.units != DistanceUnits.M:
                        raise NotImplementedError(
                            "AGL altitudes with feet are not yet implemented"
                        )
                    kwargs["altitude_lower"] = Altitude(
                        value=v.volume.altitude_lower.value + GROUND_ELEVATION,
                        reference=AltitudeDatum.W84,
                        units=v.volume.altitude_lower.units,
                    )
                else:
                    raise NotImplementedError(
                        f"{v.volume.altitude_lower.reference} altitude datum not yet supported"
                    )
            if v.volume.altitude_upper:
                if v.volume.altitude_upper.reference == AltitudeDatum.W84:
                    kwargs["altitude_upper"] = v.volume.altitude_upper
                elif v.volume.altitude_upper.reference == AltitudeDatum.SFC:
                    if v.volume.altitude_upper.units != DistanceUnits.M:
                        raise NotImplementedError(
                            "AGL altitudes with feet are not yet implemented"
                        )
                    kwargs["altitude_upper"] = Altitude(
                        value=v.volume.altitude_upper.value + GROUND_ELEVATION,
                        reference=AltitudeDatum.W84,
                        units=v.volume.altitude_upper.units,
                    )
                else:
                    raise NotImplementedError(
                        f"{v.volume.altitude_upper.reference} altitude datum not yet supported"
                    )
            v2 = Volume4D(volume=Volume3D(**kwargs))
            if v.time_start:
                v2.time_start = v.time_start
            if v.time_end:
                v2.time_end = v.time_end
            result.append(v2)
        else:
            result.append(v)
    return Volume4DCollection(result)


def op_intent_from_flightinfo(
    flight_info: FlightInfo, flight_id: str
) -> f3548_v21.OperationalIntent:
    volumes = [
        v.to_f3548v21() for v in _convert_altitudes(flight_info.basic_information.area)
    ]
    off_nominal_volumes = []

    state = flight_info.basic_information.f3548v21_op_intent_state()
    if state in (
        f3548_v21.OperationalIntentState.Nonconforming,
        f3548_v21.OperationalIntentState.Contingent,
    ):
        off_nominal_volumes = volumes
        volumes = []

    v4c = flight_info.basic_information.area

    reference = f3548_v21.OperationalIntentReference(
        id=f3548_v21.EntityID(flight_id),
        manager="UNKNOWN",
        uss_availability=f3548_v21.UssAvailabilityState.Unknown,
        version=0,
        state=state,
        ovn="UNKNOWN",
        time_start=v4c.time_start.to_f3548v21(),
        time_end=v4c.time_end.to_f3548v21(),
        uss_base_url=f"{webapp.config[KEY_BASE_URL]}/mock/scd",
        subscription_id="UNKNOWN",
    )
    if "astm_f3548_21" in flight_info and flight_info.astm_f3548_21:
        priority = flight_info.astm_f3548_21.priority
    else:
        # TODO: Ensure this function is only called when sufficient information is available, or raise ValueError
        priority = 0
    details = f3548_v21.OperationalIntentDetails(
        volumes=volumes,
        off_nominal_volumes=off_nominal_volumes,
        priority=priority,
    )
    return f3548_v21.OperationalIntent(
        reference=reference,
        details=details,
    )


def op_intent_from_flightrecord(
    flight: FlightRecord, method: str
) -> f3548_v21.OperationalIntent:
    ref = flight.op_intent.reference
    details = f3548_v21.OperationalIntentDetails(
        volumes=flight.op_intent.details.volumes,
        off_nominal_volumes=flight.op_intent.details.off_nominal_volumes,
        priority=priority_of(flight.op_intent.details),
    )
    op_intent = f3548_v21.OperationalIntent(reference=ref, details=details)
    if flight.mod_op_sharing_behavior:
        mod_op_sharing_behavior = flight.mod_op_sharing_behavior
        if mod_op_sharing_behavior.modify_sharing_methods is not None:
            if method not in mod_op_sharing_behavior.modify_sharing_methods:
                return op_intent
        op_intent = apply_overrides(
            op_intent, mod_op_sharing_behavior.modify_fields, parse_result=False
        )

    # Sanity check on the result of apply_overrides
    if not isinstance(op_intent, f3548_v21.OperationalIntent):
        raise Exception(
            f"Expected OperationalIntent, got {type(op_intent).__name__} instead. This is likely a bug in apply_overrides."
        )

    return op_intent


def query_operational_intents(
    locality: Locality,
    area_of_interest: f3548_v21.Volume4D,
) -> list[f3548_v21.OperationalIntent]:
    """Retrieve a complete set of operational intents in an area, including details.

    :param locality: Locality applicable to this query
    :param area_of_interest: Area where intersecting operational intents must be discovered
    :return: Full definition for every operational intent discovered
    """
    op_intent_refs = scd_client.query_operational_intent_references(
        utm_client, area_of_interest
    )
    tx = db.value
    get_details_for = []
    own_flights = {f.op_intent.reference.id: f for f in tx.flights.values() if f}
    result = []
    for op_intent_ref in op_intent_refs:
        if op_intent_ref.id in own_flights:
            # This is our own flight
            result.append(
                op_intent_from_flightrecord(own_flights[op_intent_ref.id], "GET")
            )
        elif (
            op_intent_ref.id in tx.cached_operations
            and tx.cached_operations[op_intent_ref.id].reference.version
            == op_intent_ref.version
        ):
            # We have a current version of this op intent cached
            result.append(tx.cached_operations[op_intent_ref.id])
        else:
            # We need to get the details for this op intent
            get_details_for.append(op_intent_ref)

    updated_op_intents = []
    for op_intent_ref in get_details_for:
        try:
            op_intent, _ = scd_client.get_operational_intent_details(
                utm_client, op_intent_ref.uss_base_url, op_intent_ref.id
            )
            updated_op_intents.append(op_intent)
        except QueryError as e:
            if op_intent_ref.uss_availability == f3548_v21.UssAvailabilityState.Down:
                # if the USS does not respond to request for details, and if it marked as down at the DSS, then we don't
                # have to fail and can assume specific values for details
                op_intent = get_down_uss_op_intent(
                    locality, area_of_interest, op_intent_ref
                )
                updated_op_intents.append(op_intent)
            else:
                # if the USS is not marked as down we just let the error bubble up
                raise e
    result.extend(updated_op_intents)

    with db.transact() as tx:
        for op_intent in updated_op_intents:
            tx.value.cached_operations[op_intent.reference.id] = op_intent

    return result


def get_down_uss_op_intent(
    locality: Locality,
    area_of_interest: f3548_v21.Volume4D,
    op_intent_ref: f3548_v21.OperationalIntentReference,
) -> f3548_v21.OperationalIntent:
    """This function determines the operational intent to be considered in case its managing USS is determined to be
     down and does not respond to the requests for details.

    Note: This function will populate volumes (for accepted or activated states) and off_nominal_volumes (for contingent
     and non-conforming states) with the area of interest that was requested. The reason is that later on the function
     `check_for_conflicts` will need to evaluate again those conflicts to determine pre-existing conflicts.
    TODO: A better approach to this issue would be to store the area in conflict when a flight is planned with a
     conflict, that way we can just retrieve the conflicting area instead of having to compute again the intersection
     between the flight to be planned and the conflicting operational intent.
    """

    # at that point the value of the OVN as it is returned by the DSS may be `Available from USS`, so we explicitly
    # remove it so that it is excluded from the key
    op_intent_ref.ovn = None

    # USS is declared as down and does not answer for details : minimum - 1
    if op_intent_ref.state == f3548_v21.OperationalIntentState.Accepted:
        return f3548_v21.OperationalIntent(
            reference=op_intent_ref,
            details=f3548_v21.OperationalIntentDetails(
                volumes=[area_of_interest],
                priority=locality.lowest_bound_priority(),
            ),
        )

    elif op_intent_ref.state == f3548_v21.OperationalIntentState.Activated:
        return f3548_v21.OperationalIntent(
            reference=op_intent_ref,
            details=f3548_v21.OperationalIntentDetails(
                volumes=[area_of_interest],
                priority=locality.highest_priority(),
            ),
        )

    elif (
        op_intent_ref.state == f3548_v21.OperationalIntentState.Contingent
        or op_intent_ref.state == f3548_v21.OperationalIntentState.Nonconforming
    ):
        return f3548_v21.OperationalIntent(
            reference=op_intent_ref,
            details=f3548_v21.OperationalIntentDetails(
                off_nominal_volumes=[area_of_interest],
                priority=locality.highest_priority(),
            ),
        )

    else:
        raise ValueError(
            f"operational intent {op_intent_ref.id}: invalid state {op_intent_ref.state}"
        )


def check_op_intent(
    new_flight: FlightRecord,
    existing_flight: FlightRecord | None,
    locality: Locality,
    log: Callable[[str], None],
) -> tuple[list[f3548_v21.EntityOVN], bool]:
    # Check the transition is valid
    state_transition_from = (
        f3548_v21.OperationalIntentState(existing_flight.op_intent.reference.state)
        if existing_flight
        else None
    )
    state_transition_to = f3548_v21.OperationalIntentState(
        new_flight.op_intent.reference.state
    )
    if not op_intent_transition_valid(state_transition_from, state_transition_to):
        raise PlanningError(
            f"Operational intent state transition from {state_transition_from} to {state_transition_to} is invalid"
        )

    # Check the priority is allowed in the locality
    priority = priority_of(new_flight.op_intent.details)
    if (
        priority > locality.highest_priority()
        or priority <= locality.lowest_bound_priority()
    ):
        raise PlanningError(
            f"Operational intent priority {priority} is outside the bounds of the locality priority range (]{locality.lowest_bound_priority()},{locality.highest_priority()}])"
        )

    if new_flight.op_intent.reference.state in (
        f3548_v21.OperationalIntentState.Accepted,
        f3548_v21.OperationalIntentState.Activated,
    ):
        # Check for intersections if the flight is nominal

        # Check for operational intents in the DSS
        log("Obtaining latest operational intent information")
        v1 = Volume4DCollection.from_interuss_scd_api(
            new_flight.op_intent.details.volumes
            + new_flight.op_intent.details.off_nominal_volumes
        )
        vol4 = v1.bounding_volume.to_f3548v21()
        op_intents = query_operational_intents(locality, vol4)

        # Check for intersections
        log(
            f"Checking for intersections with {', '.join(op_intent.reference.id for op_intent in op_intents)}"
        )
        has_conflicts = check_for_conflicts(
            new_flight.op_intent, existing_flight, op_intents, locality, log
        )

        key = [
            f3548_v21.EntityOVN(op.reference.ovn)
            for op in op_intents
            if op.reference.ovn is not None
        ]
    else:
        # Flight is not nominal and therefore doesn't need to check intersections
        key = []
        has_conflicts = False

    return key, has_conflicts


def share_op_intent(
    new_flight: FlightRecord,
    existing_flight: FlightRecord | None,
    key: list[f3548_v21.EntityOVN],
    log: Callable[[str], None],
) -> tuple[FlightRecord, dict[f3548_v21.SubscriptionUssBaseURL, Exception]]:
    """Share the operational intent reference with the DSS in compliance with ASTM F3548-21.

    Returns:
        The flight record shared;
        Notification errors if any, by subscriber.

    Raises:
        * QueryError
        * ConnectionError
        * requests.exceptions.ConnectionError
    """
    # Create operational intent in DSS
    log("Sharing operational intent with DSS")
    base_url = new_flight.op_intent.reference.uss_base_url
    req = f3548_v21.PutOperationalIntentReferenceParameters(
        extents=new_flight.op_intent.details.volumes
        + new_flight.op_intent.details.off_nominal_volumes,
        key=key,
        state=new_flight.op_intent.reference.state,
        uss_base_url=base_url,
        new_subscription=f3548_v21.ImplicitSubscriptionParameters(
            uss_base_url=base_url
        ),
    )
    if existing_flight:
        id = existing_flight.op_intent.reference.id
        log(f"Updating existing operational intent {id} in DSS")
        result = scd_client.update_operational_intent_reference(
            utm_client,
            id,
            existing_flight.op_intent.reference.ovn,
            req,
        )
    else:
        id = str(uuid.uuid4())
        log(f"Creating new operational intent {id} in DSS")
        result = scd_client.create_operational_intent_reference(utm_client, id, req)

    # Notify subscribers
    true_op_intent = f3548_v21.OperationalIntent(
        reference=result.operational_intent_reference,
        details=new_flight.op_intent.details,
    )
    record = FlightRecord(
        op_intent=true_op_intent,
        flight_info=new_flight.flight_info,
        mod_op_sharing_behavior=new_flight.mod_op_sharing_behavior,
    )
    operational_intent = op_intent_from_flightrecord(record, "POST")
    notif_errors = notify_subscribers(
        result.operational_intent_reference.id,
        operational_intent,
        result.subscribers,
        log,
    )
    return record, notif_errors


def delete_op_intent(
    op_intent_ref: f3548_v21.OperationalIntentReference, log: Callable[[str], None]
) -> dict[f3548_v21.SubscriptionUssBaseURL, Exception]:
    """Remove the operational intent reference from the DSS in compliance with ASTM F3548-21.

    Args:
        op_intent_ref: Operational intent reference to remove.
        log: Means of indicating debugging information.

    Returns:
        Notification errors if any, by subscriber.

    Raises:
        * QueryError
        * ConnectionError
        * requests.exceptions.ConnectionError
    """
    result = scd_client.delete_operational_intent_reference(
        utm_client,
        op_intent_ref.id,
        op_intent_ref.ovn,
    )
    return notify_subscribers(
        result.operational_intent_reference.id, None, result.subscribers, log
    )


def notify_subscribers(
    op_intent_id: f3548_v21.EntityID,
    op_intent: f3548_v21.OperationalIntent | None,
    subscribers: list[f3548_v21.SubscriberToNotify],
    log: Callable[[str], None],
) -> dict[f3548_v21.SubscriptionUssBaseURL, Exception]:
    """
    Notify subscribers of a changed or deleted operational intent.
    This function will attempt all notifications, even if some of them fail.

    :return: Notification errors if any, by subscriber.
    """
    notif_errors: dict[f3548_v21.SubscriptionUssBaseURL, Exception] = {}
    for subscriber in subscribers:
        update = f3548_v21.PutOperationalIntentDetailsParameters(
            operational_intent_id=op_intent_id,
            operational_intent=op_intent,
            subscriptions=subscriber.subscriptions,
        )
        log(f"Notifying {subscriber.uss_base_url}")
        try:
            scd_client.notify_operational_intent_details_changed(
                utm_client, subscriber.uss_base_url, update
            )
        except (
            ValueError,
            ConnectionError,
            requests.exceptions.ConnectionError,
            QueryError,
        ) as e:
            log(f"Failed to notify {subscriber.uss_base_url}: {str(e)}")
            notif_errors[subscriber.uss_base_url] = e

    log(f"{len(notif_errors) if notif_errors else 'No'} notifications failed")
    return notif_errors
