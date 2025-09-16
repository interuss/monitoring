import json
import uuid

import arrow
import flask
from implicitdict import ImplicitDict, StringBasedDateTime
from loguru import logger
from uas_standards.astm.f3548.v21.api import (
    ErrorReport,
    ErrorResponse,
    GetOperationalIntentDetailsResponse,
    OperationalIntentState,
    PutOperationalIntentDetailsParameters,
)
from uas_standards.interuss.automated_testing.flight_planning.v1 import api

from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.database import db as core_db
from monitoring.mock_uss.f3548v21.flight_planning import (
    check_for_local_conflits,
    op_intent_from_flightrecord,
)
from monitoring.mock_uss.flights.database import FlightRecord, db
from monitoring.monitorlib import scd


@webapp.route("/mock/scd/uss/v1/operational_intents/<entityid>", methods=["GET"])
@requires_scope(scd.SCOPE_SC)
def scdsc_get_operational_intent_details(entityid: str):
    """Implements getOperationalIntentDetails in ASTM SCD API."""

    # Look up entityid in database
    tx = db.value
    flight = None
    for f in tx.flights.values():
        if f and f.op_intent.reference.id == entityid:
            flight = f
            break

    # If requested operational intent doesn't exist, return 404
    if flight is None:
        return (
            flask.jsonify(
                ErrorResponse(
                    message=f"Operational intent {entityid} not known by this USS"
                )
            ),
            404,
        )

    # Return nominal response with details
    response = GetOperationalIntentDetailsResponse(
        operational_intent=op_intent_from_flightrecord(flight, "GET")
    )
    return flask.jsonify(response), 200


@webapp.route(
    "/mock/scd/uss/v1/operational_intents/<entityid>/telemetry", methods=["GET"]
)
@requires_scope(scd.SCOPE_CM_SA)
def scdsc_get_operational_intent_telemetry(entityid: str):
    """Implements getOperationalIntentTelemetry in ASTM SCD API."""

    # Look up entityid in database
    tx = db.value
    flight: FlightRecord | None = None
    for f in tx.flights.values():
        if f and f.op_intent.reference.id == entityid:
            flight = f
            break

    # If requested operational intent doesn't exist, return 404
    if flight is None:
        return (
            flask.jsonify(
                ErrorResponse(
                    message=f"Operational intent {entityid} not known by this USS"
                )
            ),
            404,
        )

    elif flight.op_intent.reference.state not in {
        OperationalIntentState.Contingent,
        OperationalIntentState.Nonconforming,
    }:
        return (
            flask.jsonify(
                ErrorResponse(
                    message=f"Operational intent {entityid} is not in a state that provides telemetry ({flight.op_intent.reference.state})"
                )
            ),
            409,
        )

    # TODO: implement support for telemetry
    return (
        flask.jsonify(
            ErrorResponse(
                message=f"Operational intent {entityid} has no telemetry data available."
            )
        ),
        412,
    )


@webapp.route("/mock/scd/uss/v1/operational_intents", methods=["POST"])
@requires_scope(scd.SCOPE_SC)
def scdsc_notify_operational_intent_details_changed():
    """Implements notifyOperationalIntentDetailsChanged in ASTM SCD API."""

    # We check if there is a conflits with our own flights
    try:
        op_intent_data: PutOperationalIntentDetailsParameters = ImplicitDict.parse(
            flask.request.json or {}, PutOperationalIntentDetailsParameters
        )
    except ValueError as e:
        return (
            flask.jsonify(ErrorResponse(message=f"Error parsing request: {str(e)}")),
            400,
        )

    if "operational_intent" in op_intent_data and op_intent_data.operational_intent:
        with db as tx:
            if check_for_local_conflits(
                op_intent_data.operational_intent, tx.flights.values()
            ):
                with core_db as core_tx:
                    core_tx.flight_planning_notifications.append(
                        api.UserNotification(
                            observed_at=api.Time(
                                value=StringBasedDateTime(arrow.utcnow().datetime)
                            ),
                            conflicts="Single",
                        )
                    )

    # Do nothing else because this USS is unsophisticated and polls the DSS for
    # every change in its operational intents
    return "", 204


@webapp.route("/mock/scd/uss/v1/reports", methods=["POST"])
@requires_scope(
    [scd.SCOPE_SC, scd.SCOPE_CP, scd.SCOPE_CM, scd.SCOPE_CM_SA, scd.SCOPE_AA]
)
def scdsc_make_uss_report():
    """Implements makeUssReport in ASTM SCD API."""

    # Parse the request
    try:
        report: ErrorReport = ImplicitDict.parse(flask.request.json, ErrorReport)
    except ValueError as e:
        return (
            flask.jsonify(ErrorResponse(message=f"Error parsing request: {str(e)}")),
            400,
        )

    # Construct the ErrorReport object, primarily from the request
    if "report_id" not in report or not report.report_id:
        report.report_id = str(uuid.uuid4())

    # Log the error report
    logger.info("Error report:\n" + json.dumps(report, indent=2))

    # Return the ErrorReport as the nominal response
    return flask.jsonify(report), 201
