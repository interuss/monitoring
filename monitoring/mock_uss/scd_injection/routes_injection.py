import os
import traceback
from datetime import datetime, timedelta
import time
from typing import Tuple, Optional

import flask
from implicitdict import ImplicitDict, StringBasedDateTime
from loguru import logger
import requests.exceptions

from monitoring.mock_uss.flights.planning import lock_flight, release_flight_lock
from monitoring.mock_uss.f3548v21 import utm_client
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightInfo,
    AirspaceUsageState,
)
from uas_standards.astm.f3548.v21.api import (
    PutOperationalIntentDetailsParameters,
)
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponse,
    InjectFlightResponseResult,
    DeleteFlightResponse,
    DeleteFlightResponseResult,
    ClearAreaRequest,
    ClearAreaOutcome,
    ClearAreaResponse,
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
)
import monitoring.mock_uss.uspace.flight_auth
from monitoring.monitorlib import versioning
from monitoring.monitorlib.clients import scd as scd_client
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
    return "".join(
        traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
    )


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
    try:
        json, code = inject_flight(flight_id, req_body, existing_flight)
    finally:
        release_flight_lock(flight_id, log)
    return flask.jsonify(json), code


def inject_flight(
    flight_id: str,
    req_body: MockUSSInjectFlightRequest,
    existing_flight: Optional[FlightRecord],
) -> Tuple[InjectFlightResponse, int]:
    pid = os.getpid()
    locality = get_locality()

    def log(msg: str):
        logger.debug(f"[inject_flight/{pid}:{flight_id}] {msg}")

    # Construct potential new flight
    flight_info = FlightInfo.from_scd_inject_flight_request(req_body)
    op_intent = op_intent_from_flightinfo(flight_info, flight_id)
    new_flight = FlightRecord(
        flight_info=flight_info,
        op_intent=op_intent,
        mod_op_sharing_behavior=req_body.behavior if "behavior" in req_body else None,
    )

    # Validate request
    try:
        if locality.is_uspace_applicable():
            uspace.flight_auth.validate_request(req_body)
        validate_request(req_body)
    except PlanningError as e:
        return (
            InjectFlightResponse(
                result=InjectFlightResponseResult.Rejected, notes=str(e)
            ),
            200,
        )

    step_name = "performing unknown operation"
    try:
        step_name = "checking F3548-21 operational intent"
        try:
            key = check_op_intent(new_flight, existing_flight, locality, log)
        except PlanningError as e:
            return (
                InjectFlightResponse(
                    result=InjectFlightResponseResult.Rejected,
                    notes=str(e),
                ),
                200,
            )

        step_name = "sharing operational intent in DSS"
        record = share_op_intent(new_flight, existing_flight, key, log)

        # Store flight in database
        step_name = "storing flight in database"
        log("Storing flight in database")
        with db as tx:
            tx.flights[flight_id] = record

        step_name = "returning final successful result"
        log("Complete.")

        if (
            new_flight.flight_info.basic_information.usage_state
            == AirspaceUsageState.InUse
        ):
            injection_result = InjectFlightResponseResult.ReadyToFly
        else:
            injection_result = InjectFlightResponseResult.Planned
        return (
            InjectFlightResponse(
                result=injection_result,
                operational_intent_id=new_flight.op_intent.reference.id,
            ),
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


@webapp.route("/scdsc/v1/flights/<flight_id>", methods=["DELETE"])
@requires_scope(SCOPE_SCD_QUALIFIER_INJECT)
def scdsc_delete_flight(flight_id: str) -> Tuple[str, int]:
    """Implements flight deletion in SCD automated testing injection API."""
    json, code = delete_flight(flight_id)
    return flask.jsonify(json), code


def delete_flight(flight_id) -> Tuple[DeleteFlightResponse, int]:
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
            logger.error(
                f"[delete_flight/{pid}:{flight_id}] Deadlock (now: {datetime.utcnow()}, deadline: {deadline})"
            )
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
        step_name = f"deleting operational intent {flight.op_intent.reference.id} with OVN {flight.op_intent.reference.ovn} from DSS"
        logger.debug(f"[delete_flight/{pid}:{flight_id}] {step_name}")
        result = scd_client.delete_operational_intent_reference(
            utm_client,
            flight.op_intent.reference.id,
            flight.op_intent.reference.ovn,
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
    json, code = clear_area(req)
    return flask.jsonify(json), code


def clear_area(req: ClearAreaRequest) -> Tuple[ClearAreaResponse, int]:
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
                    if record.op_intent.reference.id in deleted:
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
                logger.error(
                    f"[clear_area] Deadlock (now: {datetime.utcnow()}, deadline: {deadline})"
                )
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
