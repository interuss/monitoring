import os
import traceback
from datetime import datetime, timedelta
import time
from typing import List, Tuple
import uuid

import flask
from implicitdict import ImplicitDict, StringBasedDateTime
from loguru import logger
import requests.exceptions

from uas_standards.astm.f3548.v21 import api
from uas_standards.astm.f3548.v21.api import (
    OperationalIntent,
    PutOperationalIntentDetailsParameters,
    ImplicitSubscriptionParameters,
    PutOperationalIntentReferenceParameters,
)
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightRequest,
    InjectFlightResponse,
    InjectFlightResponseResult,
    DeleteFlightResponse,
    DeleteFlightResponseResult,
    ClearAreaRequest,
    ClearAreaOutcome,
    ClearAreaResponse,
    Capability,
    CapabilitiesResponse,
    OperationalIntentState,
)

from monitoring.mock_uss import webapp, require_config_value
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.config import KEY_BASE_URL
from monitoring.mock_uss.dynamic_configuration.configuration import get_locality
from monitoring.mock_uss.scdsc import database, utm_client
from monitoring.mock_uss.scdsc.database import db
from monitoring.mock_uss.scdsc.flight_planning import (
    validate_request,
    check_for_disallowed_conflicts,
    PlanningError,
    op_intent_transition_valid,
)
from monitoring.mock_uss.scdsc.routes_scdsc import op_intent_from_flightrecord
from monitoring.monitorlib import versioning
from monitoring.monitorlib.clients import scd as scd_client
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geo import Polygon
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from monitoring.monitorlib.idempotency import idempotent_request
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    SCOPE_SCD_QUALIFIER_INJECT,
)


require_config_value(KEY_BASE_URL)

DEADLOCK_TIMEOUT = timedelta(seconds=5)


def _make_stacktrace(e) -> str:
    return "".join(
        traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
    )


def query_operational_intents(
    area_of_interest: api.Volume4D,
) -> List[OperationalIntent]:
    """Retrieve a complete set of operational intents in an area, including details.

    :param area_of_interest: Area where intersecting operational intents must be discovered
    :return: Full definition for every operational intent discovered
    """
    op_intent_refs = scd_client.query_operational_intent_references(
        utm_client, area_of_interest
    )
    tx = db.value
    get_details_for = []
    own_flights = {f.op_intent_reference.id: f for f in tx.flights.values() if f}
    result = []
    for op_intent_ref in op_intent_refs:
        if op_intent_ref.id in own_flights:
            # This is our own flight
            result.append(op_intent_from_flightrecord(own_flights[op_intent_ref.id]))
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
        op_intent, _ = scd_client.get_operational_intent_details(
            utm_client, op_intent_ref.uss_base_url, op_intent_ref.id
        )
        updated_op_intents.append(op_intent)
    result.extend(updated_op_intents)

    with db as tx:
        for op_intent in updated_op_intents:
            tx.cached_operations[op_intent.reference.id] = op_intent

    return result


@webapp.route("/scdsc/v1/status", methods=["GET"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def scdsc_injection_status() -> Tuple[str, int]:
    """Implements USS status in SCD automated testing injection API."""
    json, code = injection_status()
    return flask.jsonify(json), code


def injection_status() -> Tuple[dict, int]:
    return (
        {"status": "Ready", "version": versioning.get_code_version()},
        200,
    )


@webapp.route("/scdsc/v1/capabilities", methods=["GET"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def scdsc_scd_capabilities() -> Tuple[str, int]:
    """Implements USS capabilities in SCD automated testing injection API."""
    json, code = scd_capabilities()
    return flask.jsonify(json), code


def scd_capabilities() -> Tuple[dict, int]:
    return (
        CapabilitiesResponse(
            capabilities=[
                Capability.BasicStrategicConflictDetection,
                Capability.FlightAuthorisationValidation,
                Capability.HighPriorityFlights,
            ]
        ),
        200,
    )


@webapp.route("/scdsc/v1/flights/<flight_id>", methods=["PUT"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
@idempotent_request()
def scdsc_inject_flight(flight_id: str) -> Tuple[str, int]:
    """Implements flight injection in SCD automated testing injection API."""
    logger.debug(f"[inject_flight/{os.getpid()}:{flight_id}] Starting handler")
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req_body: InjectFlightRequest = ImplicitDict.parse(json, InjectFlightRequest)
    except ValueError as e:
        msg = "Create flight {} unable to parse JSON: {}".format(flight_id, e)
        return msg, 400
    json, code = inject_flight(flight_id, req_body)
    return flask.jsonify(json), code


def inject_flight(flight_id: str, req_body: InjectFlightRequest) -> Tuple[dict, int]:
    pid = os.getpid()
    locality = get_locality()

    def log(msg: str):
        logger.debug(f"[inject_flight/{pid}:{flight_id}] {msg}")

    # Validate request
    log("Validating request")
    try:
        validate_request(req_body, locality)
    except PlanningError as e:
        return (
            InjectFlightResponse(
                result=InjectFlightResponseResult.Rejected, notes=str(e)
            ),
            200,
        )

    # If this is a change to an existing flight, acquire lock to that flight
    log("Acquiring lock for flight")
    deadline = datetime.utcnow() + DEADLOCK_TIMEOUT
    while True:
        with db as tx:
            if flight_id in tx.flights:
                # This is an existing flight being modified
                existing_flight = tx.flights[flight_id]
                if existing_flight and not existing_flight.locked:
                    log("Existing flight locked for update")
                    existing_flight.locked = True
                    break
            else:
                log("Request is for a new flight (lock established)")
                tx.flights[flight_id] = None
                existing_flight = None
                break
        # We found an existing flight but it was locked; wait for it to become
        # available
        time.sleep(0.5)

        if datetime.utcnow() > deadline:
            raise RuntimeError(
                f"Deadlock in inject_flight while attempting to gain access to flight {flight_id}"
            )

    step_name = "performing unknown operation"
    try:
        # Check the transition is valid
        state_transition_from = (
            OperationalIntentState(existing_flight.op_intent_reference.state)
            if existing_flight
            else None
        )
        state_transition_to = OperationalIntentState(req_body.operational_intent.state)
        if not op_intent_transition_valid(state_transition_from, state_transition_to):
            return (
                InjectFlightResponse(
                    result=InjectFlightResponseResult.Rejected,
                    notes=f"Operational intent state transition from {state_transition_from} to {state_transition_to} is invalid",
                ),
                200,
            )

        if req_body.operational_intent.state in (
            OperationalIntentState.Accepted,
            OperationalIntentState.Activated,
        ):
            # Check for intersections if the flight is nominal

            # Check for operational intents in the DSS
            step_name = "querying for operational intents"
            log("Obtaining latest operational intent information")
            v1 = Volume4DCollection.from_interuss_scd_api(
                req_body.operational_intent.volumes
                + req_body.operational_intent.off_nominal_volumes
            )
            vol4 = v1.bounding_volume.to_f3548v21()
            op_intents = query_operational_intents(vol4)

            # Check for intersections
            step_name = "checking for intersections"
            log(
                f"Checking for intersections with {', '.join(op_intent.reference.id for op_intent in op_intents)}"
            )
            try:
                check_for_disallowed_conflicts(
                    req_body, existing_flight, op_intents, locality, log
                )
            except PlanningError as e:
                return (
                    InjectFlightResponse(
                        result=InjectFlightResponseResult.ConflictWithFlight,
                        notes=str(e),
                    ),
                    200,
                )

            key = [op.reference.ovn for op in op_intents]
        else:
            # Flight is not nominal and therefore doesn't need to check intersections
            key = []

        # Create operational intent in DSS
        step_name = "sharing operational intent in DSS"
        log("Sharing operational intent with DSS")
        base_url = "{}/mock/scd".format(webapp.config[KEY_BASE_URL])
        req = PutOperationalIntentReferenceParameters(
            extents=req_body.operational_intent.volumes
            + req_body.operational_intent.off_nominal_volumes,
            key=key,
            state=req_body.operational_intent.state,
            uss_base_url=base_url,
            new_subscription=ImplicitSubscriptionParameters(uss_base_url=base_url),
        )
        if existing_flight:
            id = existing_flight.op_intent_reference.id
            step_name = f"updating existing operational intent {id} in DSS"
            log(step_name)
            result = scd_client.update_operational_intent_reference(
                utm_client,
                id,
                existing_flight.op_intent_reference.ovn,
                req,
            )
        else:
            id = str(uuid.uuid4())
            step_name = f"creating new operational intent {id} in DSS"
            log(step_name)
            result = scd_client.create_operational_intent_reference(utm_client, id, req)

        # Notify subscribers
        subscriber_list = ", ".join(s.uss_base_url for s in result.subscribers)
        step_name = f"notifying subscribers {{{subscriber_list}}}"
        operational_intent = OperationalIntent(
            reference=result.operational_intent_reference,
            details=req_body.operational_intent,
        )
        for subscriber in result.subscribers:
            if subscriber.uss_base_url == base_url:
                # Do not notify ourselves
                continue
            update = PutOperationalIntentDetailsParameters(
                operational_intent_id=result.operational_intent_reference.id,
                operational_intent=operational_intent,
                subscriptions=subscriber.subscriptions,
            )
            log(f"Notifying subscriber at {subscriber.uss_base_url}")
            step_name = f"notifying subscriber {{{subscriber.uss_base_url}}}"
            scd_client.notify_operational_intent_details_changed(
                utm_client, subscriber.uss_base_url, update
            )

        # Store flight in database
        step_name = "storing flight in database"
        log("Storing flight in database")
        record = database.FlightRecord(
            op_intent_reference=result.operational_intent_reference,
            op_intent_injection=req_body.operational_intent,
            flight_authorisation=req_body.flight_authorisation,
        )
        with db as tx:
            tx.flights[flight_id] = record

        step_name = "returning final successful result"
        log("Complete.")

        if (
            result.operational_intent_reference.state
            == OperationalIntentState.Activated
        ):
            injection_result = InjectFlightResponseResult.ReadyToFly
        else:
            injection_result = InjectFlightResponseResult.Planned
        return (
            InjectFlightResponse(result=injection_result, operational_intent_id=id),
            200,
        )
    except (ValueError, ConnectionError) as e:
        notes = (
            f"{e.__class__.__name__} while {step_name} for flight {flight_id}: {str(e)}"
        )
        return (
            InjectFlightResponse(result=InjectFlightResponseResult.Failed, notes=notes),
            200,
        )
    except requests.exceptions.ConnectionError as e:
        notes = f"Connection error to {e.request.method} {e.request.url} while {step_name} for flight {flight_id}: {str(e)}"
        response = InjectFlightResponse(
            result=InjectFlightResponseResult.Failed, notes=notes
        )
        response["stacktrace"] = _make_stacktrace(e)
        return response, 200
    except QueryError as e:
        notes = f"Unexpected response from remote server while {step_name} for flight {flight_id}: {str(e)}"
        response = InjectFlightResponse(
            result=InjectFlightResponseResult.Failed, notes=notes
        )
        response["queries"] = e.queries
        response["stacktrace"] = e.stacktrace
        return response, 200
    finally:
        with db as tx:
            if tx.flights[flight_id]:
                # FlightRecord was a true existing flight
                log(f"Releasing placeholder for flight_id {flight_id}")
                tx.flights[flight_id].locked = False
            else:
                # FlightRecord was just a placeholder for a new flight
                log("Releasing lock on existing flight_id {flight_id}")
                del tx.flights[flight_id]


@webapp.route("/scdsc/v1/flights/<flight_id>", methods=["DELETE"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def scdsc_delete_flight(flight_id: str) -> Tuple[str, int]:
    """Implements flight deletion in SCD automated testing injection API."""
    json, code = delete_flight(flight_id)
    return flask.jsonify(json), code


def delete_flight(flight_id) -> Tuple[dict, int]:
    pid = os.getpid()
    logger.debug(f"[delete_flight/{pid}:{flight_id}] Acquiring flight")
    deadline = datetime.utcnow() + DEADLOCK_TIMEOUT
    while True:
        with db as tx:
            if flight_id in tx.flights:
                flight = tx.flights[flight_id]
                if flight and not flight.locked:
                    # FlightRecord was a true existing flight not being mutated anywhere else
                    del tx.flights[flight_id]
                    break
            else:
                # No FlightRecord found
                flight = None
                break
        # There is a race condition with another handler to create or modify the requested flight; wait for that to resolve
        time.sleep(0.5)

        if datetime.utcnow() > deadline:
            logger.debug(f"[delete_flight/{pid}:{flight_id}] Deadlock")
            raise RuntimeError(
                f"Deadlock in delete_flight while attempting to gain access to flight {flight_id}"
            )

    if flight is None:
        return (
            DeleteFlightResponse(
                result=DeleteFlightResponseResult.Failed,
                notes="Flight {} does not exist".format(flight_id),
            ),
            200,
        )

    # Delete operational intent from DSS
    step_name = "performing unknown operation"
    try:
        step_name = f"deleting operational intent {flight.op_intent_reference.id} with OVN {flight.op_intent_reference.ovn} from DSS"
        logger.debug(f"[delete_flight/{pid}:{flight_id}] {step_name}")
        result = scd_client.delete_operational_intent_reference(
            utm_client,
            flight.op_intent_reference.id,
            flight.op_intent_reference.ovn,
        )

        step_name = "notifying subscribers"
        base_url = "{}/mock/scd".format(webapp.config[KEY_BASE_URL])
        for subscriber in result.subscribers:
            if subscriber.uss_base_url == base_url:
                # Do not notify ourselves
                continue
            update = PutOperationalIntentDetailsParameters(
                operational_intent_id=result.operational_intent_reference.id,
                subscriptions=subscriber.subscriptions,
            )
            logger.debug(
                f"[delete_flight/{pid}:{flight_id}] Notifying {subscriber.uss_base_url}"
            )
            scd_client.notify_operational_intent_details_changed(
                utm_client, subscriber.uss_base_url, update
            )
    except (ValueError, ConnectionError) as e:
        notes = (
            f"{e.__class__.__name__} while {step_name} for flight {flight_id}: {str(e)}"
        )
        logger.debug(f"[delete_flight/{pid}:{flight_id}] {notes}")
        return (
            DeleteFlightResponse(result=DeleteFlightResponseResult.Failed, notes=notes),
            200,
        )
    except requests.exceptions.ConnectionError as e:
        notes = f"Connection error to {e.request.method} {e.request.url} while {step_name} for flight {flight_id}: {str(e)}"
        logger.debug(f"[delete_flight/{pid}:{flight_id}] {notes}")
        response = DeleteFlightResponse(
            result=DeleteFlightResponseResult.Failed, notes=notes
        )
        response["stacktrace"] = _make_stacktrace(e)
        return response, 200
    except QueryError as e:
        notes = f"Unexpected response from remote server while {step_name} for flight {flight_id}: {str(e)}"
        logger.debug(f"[delete_flight/{pid}:{flight_id}] {notes}")
        response = DeleteFlightResponse(
            result=DeleteFlightResponseResult.Failed, notes=notes
        )
        response["queries"] = e.queries
        response["stacktrace"] = e.stacktrace
        return response, 200

    logger.debug(f"[delete_flight/{pid}:{flight_id}] Complete.")
    return DeleteFlightResponse(result=DeleteFlightResponseResult.Closed), 200


@webapp.route("/scdsc/v1/clear_area_requests", methods=["POST"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
@idempotent_request()
def scdsc_clear_area() -> Tuple[str, int]:
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req: ClearAreaRequest = ImplicitDict.parse(json, ClearAreaRequest)
    except ValueError as e:
        msg = "Unable to parse ClearAreaRequest JSON request: {}".format(e)
        return msg, 400
    json, code = clear_area(req)
    return flask.jsonify(json), code


def clear_area(req: ClearAreaRequest) -> Tuple[dict, int]:
    def make_result(success: bool, msg: str) -> ClearAreaResponse:
        return ClearAreaResponse(
            outcome=ClearAreaOutcome(
                success=success,
                message=msg,
                timestamp=StringBasedDateTime(datetime.utcnow()),
            ),
            request=req,
        )

    step_name = "performing unknown operation"
    try:
        # Find operational intents in the DSS
        step_name = "constructing DSS operational intent query"
        # TODO: Simply use the req.extent 4D volume more directly
        extent = Volume4D.from_interuss_scd_api(req.extent)
        start_time = extent.time_start.datetime
        end_time = extent.time_end.datetime
        area = extent.rect_bounds
        alt_lo = extent.volume.altitude_lower_wgs84_m()
        alt_hi = extent.volume.altitude_upper_wgs84_m()
        vol4 = Volume4D.from_values(
            start_time,
            end_time,
            alt_lo,
            alt_hi,
            polygon=Polygon.from_latlng_rect(latlngrect=area),
        ).to_f3548v21()
        step_name = "finding operational intents in the DSS"
        op_intent_refs = scd_client.query_operational_intent_references(
            utm_client, vol4
        )

        # Try to delete every operational intent found
        op_intent_ids = ", ".join(op_intent_ref.id for op_intent_ref in op_intent_refs)
        step_name = f"deleting operational intents {{{op_intent_ids}}}"
        dss_deletion_results = {}
        deleted = set()
        for op_intent_ref in op_intent_refs:
            try:
                scd_client.delete_operational_intent_reference(
                    utm_client, op_intent_ref.id, op_intent_ref.ovn
                )
                dss_deletion_results[op_intent_ref.id] = "Deleted from DSS"
                deleted.add(op_intent_ref.id)
            except QueryError as e:
                dss_deletion_results[op_intent_ref.id] = {
                    "deletion_success": False,
                    "message": str(e),
                    "queries": e.queries,
                    "stacktrace": e.stacktrace,
                }

        # Delete corresponding flight injections and cached operational intents
        step_name = "deleting flight injections and cached operational intents"
        deadline = datetime.utcnow() + DEADLOCK_TIMEOUT
        while True:
            pending_flights = set()
            with db as tx:
                flights_to_delete = []
                for flight_id, record in tx.flights.items():
                    if record is None or record.locked:
                        pending_flights.add(flight_id)
                        continue
                    if record.op_intent_reference.id in deleted:
                        flights_to_delete.append(flight_id)
                for flight_id in flights_to_delete:
                    del tx.flights[flight_id]

                cache_deletions = []
                for op_intent_id in deleted:
                    if op_intent_id in tx.cached_operations:
                        del tx.cached_operations[op_intent_id]
                        cache_deletions.append(op_intent_id)

            if not pending_flights:
                break
            time.sleep(0.5)

            if datetime.utcnow() > deadline:
                raise RuntimeError(
                    f"Deadlock in clear_area while attempting to gain access to flight(s) {', '.join(pending_flights)}"
                )

    except (ValueError, ConnectionError) as e:
        msg = f"{e.__class__.__name__} while {step_name}: {str(e)}"
        return make_result(False, msg), 200
    except requests.exceptions.ConnectionError as e:
        msg = f"Connection error to {e.request.method} {e.request.url} while {step_name}: {str(e)}"
        result = make_result(False, msg)
        result["stacktrace"] = _make_stacktrace(e)
        return result, 200
    except QueryError as e:
        msg = f"Unexpected response from remote server while {step_name}: {str(e)}"
        result = make_result(False, msg)
        result["queries"] = e.queries
        result["stacktrace"] = e.stacktrace
        return result, 200

    result = make_result(True, "Area clearing attempt complete")
    result["dss_deletions"] = dss_deletion_results
    result["flight_deletions"] = (flights_to_delete,)
    result["cache_deletions"] = cache_deletions
    return result, 200
