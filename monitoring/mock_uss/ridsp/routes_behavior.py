import flask
from implicitdict import ImplicitDict

from monitoring.mock_uss.app import webapp

from .behavior import ServiceProviderBehavior
from .database import db


@webapp.route("/ridsp/behavior", methods=["PUT"])
def ridsp_set_dp_behavior() -> tuple[str, int] | flask.Response:
    """Set the behavior of the mock Display Provider."""
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        dp_behavior = ImplicitDict.parse(json, ServiceProviderBehavior)
    except ValueError as e:
        msg = f"Change behavior for Service Provider unable to parse JSON: {e}"
        return msg, 400

    with db.transact() as tx:
        tx.value.behavior = dp_behavior

    return flask.jsonify(dp_behavior)


@webapp.route("/ridsp/behavior", methods=["GET"])
def ridsp_get_dp_behavior() -> flask.Response:
    """Get the behavior of the mock Display Provider."""
    return flask.jsonify(db.value.behavior)
