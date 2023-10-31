import flask

from monitoring.mock_uss.f3548v21.flight_planning import op_intent_from_flightrecord
from monitoring.monitorlib import scd
from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.flights.database import db
from uas_standards.astm.f3548.v21.api import (
    ErrorResponse,
    GetOperationalIntentDetailsResponse,
)


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
                    message="Operational intent {} not known by this USS".format(
                        entityid
                    )
                )
            ),
            404,
        )

    # Return nominal response with details
    response = GetOperationalIntentDetailsResponse(
        operational_intent=op_intent_from_flightrecord(flight, "GET")
    )
    return flask.jsonify(response), 200


@webapp.route("/mock/scd/uss/v1/operational_intents", methods=["POST"])
@requires_scope(scd.SCOPE_SC)
def scdsc_notify_operational_intent_details_changed():
    """Implements notifyOperationalIntentDetailsChanged in ASTM SCD API."""

    # Do nothing because this USS is unsophisticated and polls the DSS for every
    # change in its operational intents
    return "", 204


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
