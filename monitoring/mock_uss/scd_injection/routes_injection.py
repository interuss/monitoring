import os
import traceback
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, Dict

import flask
from implicitdict import ImplicitDict, StringBasedDateTime
from loguru import logger
import requests.exceptions

from monitoring.mock_uss.flights.planning import (
    lock_flight,
    release_flight_lock,
    delete_flight_record,
)
from monitoring.mock_uss.f3548v21 import utm_client
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightInfo,
    FlightID,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResponse,
    PlanningActivityResult,
    FlightPlanStatus,
)
from uas_standards.astm.f3548.v21 import api as f3548v21
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_api
from uas_standards.interuss.automated_testing.scd.v1.api import (
    DeleteFlightResponse,
    DeleteFlightResponseResult,
    ClearAreaRequest,
    ClearAreaOutcome,
    Capability,
    CapabilitiesResponse,
)

from monitoring.mock_uss import webapp, require_config_value, uspace
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.config import KEY_BASE_URL
from monitoring.mock_uss.dynamic_configuration.configuration import get_locality
from monitoring.mock_uss.flights.database import db, FlightRecord
from monitoring.mock_uss.f3548v21.flight_planning import (
    validate_request,
    PlanningError,
    check_op_intent,
    share_op_intent,
    op_intent_from_flightinfo,
    delete_op_intent,
)
import monitoring.mock_uss.uspace.flight_auth
from monitoring.monitorlib import versioning
from monitoring.monitorlib.clients import scd as scd_client
from monitoring.monitorlib.clients.flight_planning.planning import ClearAreaResponse
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geo import Polygon
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.idempotency import idempotent_request
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    SCOPE_SCD_QUALIFIER_INJECT,
)
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUSSInjectFlightRequest,
)

require_config_value(KEY_BASE_URL)

DEADLOCK_TIMEOUT = timedelta(seconds=5)


def _make_stacktrace(e) -> str:
    return "".join(traceback.format_exception(e))


@webapp.route("/scdsc/v1/status", methods=["GET"])
@requires_scope(SCOPE_SCD_QUALIFIER_INJECT)
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
@requires_scope(SCOPE_SCD_QUALIFIER_INJECT)
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
@requires_scope(SCOPE_SCD_QUALIFIER_INJECT)
@idempotent_request()
def scdsc_inject_flight(flight_id: str) -> Tuple[str, int]:
    """Implements flight injection in SCD automated testing injection API."""

    def log(msg):
        logger.debug(f"[inject_flight/{os.getpid()}:{flight_id}] {msg}")

    log("Starting handler")
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req_body = ImplicitDict.parse(json, MockUSSInjectFlightRequest)
    except ValueError as e:
        msg = "Create flight {} unable to parse JSON: {}".format(flight_id, e)
        return msg, 400
    existing_flight = lock_flight(flight_id, log)

    # Construct potential new flight
    flight_info = FlightInfo.from_scd_inject_flight_request(req_body)
    op_intent = op_intent_from_flightinfo(flight_info, flight_id)
    new_flight = FlightRecord(
        flight_info=flight_info,
        op_intent=op_intent,
        mod_op_sharing_behavior=req_body.behavior if "behavior" in req_body else None,
    )

    try:
        resp = inject_flight(flight_id, new_flight, existing_flight)
    finally:
        release_flight_lock(flight_id, log)
    return flask.jsonify(resp.to_inject_flight_response()), 200


def inject_flight(
    flight_id: str,
    new_flight: FlightRecord,
    existing_flight: Optional[FlightRecord],
) -> PlanningActivityResponse:
    pid = os.getpid()
    locality = get_locality()

    def log(msg: str):
        logger.debug(f"[inject_flight/{pid}:{flight_id}] {msg}")

    old_status = FlightPlanStatus.from_flightinfo(
        existing_flight.flight_info if existing_flight else None
    )

    def unsuccessful(
        result: PlanningActivityResult, msg: str
    ) -> PlanningActivityResponse:
        return PlanningActivityResponse(
            flight_id=flight_id,
            queries=[],
            activity_result=result,
            flight_plan_status=old_status,
            notes=msg,
        )

    # Validate request
    try:
        if locality.is_uspace_applicable():
            uspace.flight_auth.validate_request(new_flight.flight_info)
        validate_request(new_flight.op_intent)
    except PlanningError as e:
        return unsuccessful(PlanningActivityResult.Rejected, str(e))

    step_name = "performing unknown operation"
    notes: Optional[str] = None
    try:
        step_name = "checking F3548-21 operational intent"
        try:
            key = check_op_intent(new_flight, existing_flight, locality, log)
        except PlanningError as e:
            return unsuccessful(PlanningActivityResult.Rejected, str(e))

        step_name = "sharing operational intent in DSS"
        record, notif_errors = share_op_intent(new_flight, existing_flight, key, log)
        if notif_errors:
            notif_errors_messages = [
                f"{url}: {str(err)}" for url, err in notif_errors.items()
            ]
            notes = f"Injection succeeded, but notification to some subscribers failed: {'; '.join(notif_errors_messages)}"
            log(notes)

        # Store flight in database
        step_name = "storing flight in database"
        log("Storing flight in database")
        with db as tx:
            tx.flights[flight_id] = record

        step_name = "returning final successful result"
        log("Complete.")

        return PlanningActivityResponse(
            flight_id=flight_id,
            queries=[],  # TODO: Add queries used
            activity_result=PlanningActivityResult.Completed,
            flight_plan_status=FlightPlanStatus.from_flightinfo(record.flight_info),
            notes=notes,
        )
    except (ValueError, ConnectionError) as e:
        notes = (
            f"{e.__class__.__name__} while {step_name} for flight {flight_id}: {str(e)}"
        )
        return unsuccessful(PlanningActivityResult.Failed, notes)
    except requests.exceptions.ConnectionError as e:
        notes = f"Connection error to {e.request.method} {e.request.url} while {step_name} for flight {flight_id}: {str(e)}"
        response = unsuccessful(PlanningActivityResult.Failed, notes)
        response["stacktrace"] = _make_stacktrace(e)
        return response
    except QueryError as e:
        notes = f"Unexpected response from remote server while {step_name} for flight {flight_id}: {str(e)}"
        response = unsuccessful(PlanningActivityResult.Failed, notes)
        response["queries"] = e.queries
        response["stacktrace"] = e.stacktrace
        return response


@webapp.route("/scdsc/v1/flights/<flight_id>", methods=["DELETE"])
@requires_scope(SCOPE_SCD_QUALIFIER_INJECT)
def scdsc_delete_flight(flight_id: str) -> Tuple[str, int]:
    """Implements flight deletion in SCD automated testing injection API."""
    del_resp = delete_flight(flight_id)

    if del_resp.activity_result == PlanningActivityResult.Completed:
        if del_resp.flight_plan_status != FlightPlanStatus.Closed:
            raise RuntimeError(
                f"delete_flight indicated {del_resp.activity_result}, but flight_plan_status was '{del_resp.flight_plan_status}' rather than Closed"
            )
        result = DeleteFlightResponseResult.Closed
        if "notes" in del_resp and del_resp.notes:
            notes = del_resp.notes
        else:
            notes = None
    else:
        result = DeleteFlightResponseResult.Failed
        notes = f"delete_flight indicated `activity_result`={del_resp.activity_result}, `flight_plan_status`={del_resp.flight_plan_status}"
        if "notes" in del_resp and del_resp.notes:
            notes += ": " + del_resp.notes
    resp = DeleteFlightResponse(result=result)
    if notes is not None:
        resp.notes = notes
    return flask.jsonify(resp), 200


def delete_flight(flight_id) -> PlanningActivityResponse:
    pid = os.getpid()

    def log(msg: str):
        logger.debug(f"[delete_flight/{pid}:{flight_id}] {msg}")

    log("Acquiring and deleting flight")
    flight = delete_flight_record(flight_id)

    old_status = FlightPlanStatus.from_flightinfo(
        flight.flight_info if flight else None
    )

    def unsuccessful(msg: str) -> PlanningActivityResponse:
        return PlanningActivityResponse(
            flight_id=flight_id,
            queries=[],
            activity_result=PlanningActivityResult.Failed,
            flight_plan_status=old_status,
            notes=msg,
        )

    if flight is None:
        return unsuccessful("Flight {} does not exist".format(flight_id))

    # Delete operational intent from DSS
    step_name = "performing unknown operation"
    notes: Optional[str] = None
    try:
        step_name = f"deleting operational intent {flight.op_intent.reference.id} with OVN {flight.op_intent.reference.ovn} from DSS"
        log(step_name)
        notif_errors = delete_op_intent(flight.op_intent.reference, log)
        if notif_errors:
            notif_errors_messages = [
                f"{url}: {str(err)}" for url, err in notif_errors.items()
            ]
            notes = f"Deletion succeeded, but notification to some subscribers failed: {'; '.join(notif_errors_messages)}"
            log(notes)

    except (ValueError, ConnectionError) as e:
        notes = (
            f"{e.__class__.__name__} while {step_name} for flight {flight_id}: {str(e)}"
        )
        log(notes)
        return unsuccessful(notes)
    except requests.exceptions.ConnectionError as e:
        notes = f"Connection error to {e.request.method} {e.request.url} while {step_name} for flight {flight_id}: {str(e)}"
        log(notes)
        response = unsuccessful(notes)
        response["stacktrace"] = _make_stacktrace(e)
        return response
    except QueryError as e:
        notes = f"Unexpected response from remote server while {step_name} for flight {flight_id}: {str(e)}"
        log(notes)
        response = unsuccessful(notes)
        response["queries"] = e.queries
        response["stacktrace"] = e.stacktrace
        return response

    log("Complete.")
    return PlanningActivityResponse(
        flight_id=flight_id,
        queries=[],
        activity_result=PlanningActivityResult.Completed,
        flight_plan_status=FlightPlanStatus.Closed,
        notes=notes,
    )


@webapp.route("/scdsc/v1/clear_area_requests", methods=["POST"])
@requires_scope(SCOPE_SCD_QUALIFIER_INJECT)
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
    clear_resp = clear_area(Volume4D.from_interuss_scd_api(req.extent))

    resp = scd_api.ClearAreaResponse(
        outcome=ClearAreaOutcome(
            success=clear_resp.success,
            message="See `details` field in response for more information",
            timestamp=StringBasedDateTime(datetime.utcnow()),
        ),
    )
    resp["request"] = req
    resp["details"] = clear_resp

    return flask.jsonify(resp), 200


def clear_area(extent: Volume4D) -> ClearAreaResponse:
    flights_deleted: List[FlightID] = []
    flight_deletion_errors: Dict[FlightID, dict] = {}
    op_intents_removed: List[f3548v21.EntityOVN] = []
    op_intent_removal_errors: Dict[f3548v21.EntityOVN, dict] = {}

    def make_result(error: Optional[dict] = None) -> ClearAreaResponse:
        resp = ClearAreaResponse(
            flights_deleted=flights_deleted,
            flight_deletion_errors=flight_deletion_errors,
            op_intents_removed=op_intents_removed,
            op_intent_removal_errors=op_intent_removal_errors,
        )
        if error is not None:
            resp.error = error
        return resp

    step_name = "performing unknown operation"
    try:
        # Find every operational intent in the DSS relevant to the extent
        step_name = "constructing DSS operational intent query"
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
        op_intent_ids = {oi.id for oi in op_intent_refs}

        # Try to remove all relevant flights normally
        for flight_id, flight in db.value.flights.items():
            # TODO: Check for intersection with flight's area rather than just relying on DSS query
            if flight.op_intent.reference.id not in op_intent_ids:
                continue

            del_resp = delete_flight(flight_id)
            if (
                del_resp.activity_result == PlanningActivityResult.Completed
                and del_resp.flight_plan_status == FlightPlanStatus.Closed
            ):
                flights_deleted.append(flight_id)
                op_intents_removed.append(flight.op_intent.reference.id)
            else:
                notes = f"Deleting known flight {flight_id} {del_resp.activity_result} with `flight_plan_status`={del_resp.flight_plan_status}"
                if "notes" in del_resp and del_resp.notes:
                    notes += ": " + del_resp.notes
                flight_deletion_errors[flight_id] = {"notes": notes}

        # Try to delete every remaining operational intent that we manage
        self_sub = utm_client.auth_adapter.get_sub()
        op_intent_refs = [
            oi
            for oi in op_intent_refs
            if oi.id not in op_intents_removed and oi.manager == self_sub
        ]
        op_intent_ids_str = ", ".join(
            op_intent_ref.id for op_intent_ref in op_intent_refs
        )
        step_name = f"deleting operational intents {{{op_intent_ids_str}}}"
        for op_intent_ref in op_intent_refs:
            try:
                scd_client.delete_operational_intent_reference(
                    utm_client, op_intent_ref.id, op_intent_ref.ovn
                )
                op_intents_removed.append(op_intent_ref.id)
            except QueryError as e:
                op_intent_removal_errors[op_intent_ref.id] = {
                    "message": str(e),
                    "queries": e.queries,
                    "stacktrace": e.stacktrace,
                }

        # Clear the op intent cache for every op intent removed
        with db as tx:
            for op_intent_id in op_intents_removed:
                if op_intent_id in tx.cached_operations:
                    del tx.cached_operations[op_intent_id]

    except (ValueError, ConnectionError) as e:
        msg = f"{e.__class__.__name__} while {step_name}: {str(e)}"
        return make_result({"message": msg})
    except requests.exceptions.ConnectionError as e:
        msg = f"Connection error to {e.request.method} {e.request.url} while {step_name}: {str(e)}"
        return make_result({"message": msg, "stacktrace": _make_stacktrace(e)})
    except QueryError as e:
        msg = f"Unexpected response from remote server while {step_name}: {str(e)}"
        return make_result(
            {"message": msg, "queries": e.queries, "stacktrace": e.stacktrace}
        )

    return make_result()
