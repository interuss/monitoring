import flask

from monitoring.monitorlib import scd
from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.scdsc.database import db, FlightRecord
from monitoring.monitorlib.mock_uss_interface import call_res_hooks


@webapp.route("/mock/scd/uss/v1/operational_intents/<entityid>", methods=["GET"])
@requires_scope([scd.SCOPE_SC])
def scdsc_get_operational_intent_details(entityid: str):
    """Implements getOperationalIntentDetails in ASTM SCD API."""
    # Look up entityid in database
    tx = db.value
    flight = None
    for f in tx.flights.values():
        if f.op_intent_reference.id == entityid:
            flight = f
            break

    response = None
    status_code = None

    # If requested operational intent doesn't exist, return 404
    if flight is None:
        response = scd.ErrorResponse(
            message="Operational intent {} not known by this USS".format(entityid)
        )
        status_code = 404
    else:
        # Return nominal response with details
        response = scd.GetOperationalIntentDetailsResponse(
            operational_intent=op_intent_from_flightrecord(flight),
        )
        status_code = 200
    # Return nominal response with details

    return flask.make_response(response, status_code)


def op_intent_from_flightrecord(flight: FlightRecord) -> scd.OperationalIntent:
    return scd.OperationalIntent(
        reference=flight.op_intent_reference,
        details=scd.OperationalIntentDetails(
            volumes=flight.op_intent_injection.volumes,
            off_nominal_volumes=flight.op_intent_injection.off_nominal_volumes,
            priority=flight.op_intent_injection.priority,
        ),
    )


@webapp.route("/mock/scd/uss/v1/operational_intents", methods=["POST"])
@requires_scope([scd.SCOPE_SC])
def scdsc_notify_operational_intent_details_changed():
    """Implements notifyOperationalIntentDetailsChanged in ASTM SCD API."""

    # Do nothing because this USS is unsophisticated and polls the DSS for every
    # change in its operational intents
    resp = flask.make_response("", 204)
    return resp


@webapp.route("/mock/scd/uss/v1/reports", methods=["POST"])
@requires_scope(
    [scd.SCOPE_SC, scd.SCOPE_CP, scd.SCOPE_CM, scd.SCOPE_CM_SA, scd.SCOPE_AA]
)
def scdsc_make_uss_report():
    """Implements makeUssReport in ASTM SCD API."""

    return flask.jsonify({"message": "Not yet implemented"}), 500

    # Parse the request
    # TODO: Implement

    # Construct the ErrorReport object, primarily from the request
    # TODO: Implement

    # Do not store the ErrorReport (in this diagnostic implementation)

    # Return the ErrorReport as the nominal response
    # TODO: Implement


@webapp.after_request
def process(response):
    req = flask.request
    call_res_hooks(req, response)
    return response
