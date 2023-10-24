from typing import Tuple

import flask
from implicitdict import ImplicitDict

from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope, MOCK_USS_CONFIG_SCOPE
from monitoring.mock_uss.dynamic_configuration.configuration import db, get_locality
from monitoring.monitorlib.clients.mock_uss.locality import (
    PutLocalityRequest,
    GetLocalityResponse,
)
from monitoring.monitorlib.locality import Locality


@webapp.route("/configuration/locality", methods=["GET"])
def locality_get() -> Tuple[str, int]:
    return flask.jsonify(
        GetLocalityResponse(locality_code=get_locality().locality_code())
    )


@webapp.route("/configuration/locality", methods=["PUT"])
@requires_scope(MOCK_USS_CONFIG_SCOPE)  # TODO: use separate public key for this
def locality_set() -> Tuple[str, int]:
    """Set the locality of the mock_uss."""
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req: PutLocalityRequest = ImplicitDict.parse(json, PutLocalityRequest)
    except ValueError as e:
        msg = f"Change locality unable to parse JSON: {str(e)}"
        return msg, 400

    # Make sure this is a valid locality
    try:
        Locality.from_locale(req.locality_code)
    except ValueError as e:
        msg = f"Invalid locality_code: {str(e)}"
        return msg, 400

    with db as tx:
        tx.locale = req.locality_code

    return flask.jsonify(
        GetLocalityResponse(locality_code=get_locality().locality_code())
    )
