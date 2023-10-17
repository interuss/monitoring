from typing import Tuple

import flask
from loguru import logger
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash

from monitoring.monitorlib import auth_validation, versioning
from .app import webapp, basic_auth, users


@webapp.route("/")
def root() -> Tuple[str, int]:
    return "ok", 200


@webapp.route("/favicon.ico")
def favicon():
    flask.abort(404)


@webapp.route("/status")
@basic_auth.login_required
def status():
    return "atproxy ok {}".format(versioning.get_code_version())


@webapp.errorhandler(Exception)
def handle_exception(e):
    logger.error("Reporting exception {}: {}", type(e).__name__, str(e))
    if isinstance(e, HTTPException):
        return e
    elif isinstance(e, auth_validation.InvalidScopeError):
        return (
            flask.jsonify(
                {
                    "message": "Invalid scope; expected one of {%s}, but received only {%s}"
                    % (" ".join(e.permitted_scopes), " ".join(e.provided_scopes))
                }
            ),
            403,
        )
    elif isinstance(e, auth_validation.InvalidAccessTokenError):
        return flask.jsonify({"message": e.message}), 401
    elif isinstance(e, auth_validation.ConfigurationError):
        return (
            flask.jsonify(
                {"message": "Auth validation configuration error: " + e.message}
            ),
            500,
        )
    elif isinstance(e, ValueError):
        return flask.jsonify({"message": str(e)}), 400

    return (
        flask.jsonify({"message": "Unhandled {}: {}".format(type(e).__name__, str(e))}),
        500,
    )


@basic_auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users[username], password):
        return username


from . import routes_handler
from . import routes_rid_observation
from . import routes_rid_injection
from . import routes_scd
