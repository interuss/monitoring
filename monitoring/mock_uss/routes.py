import traceback

import flask
from werkzeug.exceptions import HTTPException

from monitoring.mock_uss.app import enabled_services, webapp
from monitoring.mock_uss.logging import disable_log_reporting_for_request
from monitoring.monitorlib import auth_validation, versioning

from ..monitorlib.errors import stacktrace_string


@webapp.route("/status")
def status():
    return "Mock USS ok {}; hosting {}".format(
        versioning.get_code_version(), ", ".join(enabled_services)
    )


@webapp.route("/favicon.ico")
def favicon():
    flask.abort(404)


@webapp.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    elif isinstance(e, auth_validation.InvalidScopeError):
        disable_log_reporting_for_request()
        return (
            flask.jsonify(
                {
                    "message": "Invalid scope; expected one of {{{}}}, but received only {{{}}}".format(
                        " ".join(e.permitted_scopes), " ".join(e.provided_scopes)
                    )
                }
            ),
            403,
        )
    elif isinstance(e, auth_validation.InvalidAccessTokenError):
        disable_log_reporting_for_request()
        return flask.jsonify({"message": e.message}), 401
    elif isinstance(e, auth_validation.ConfigurationError):
        return (
            flask.jsonify(
                {"message": "Auth validation configuration error: " + e.message}
            ),
            500,
        )
    elif isinstance(e, ValueError):
        traceback.print_exc()
        return (
            flask.jsonify({"message": str(e), "stacktrace": stacktrace_string(e)}),
            400,
        )
    traceback.print_exc()
    return (
        flask.jsonify(
            {
                "message": f"Unhandled {type(e).__name__}: {str(e)}",
                "stacktrace": stacktrace_string(e),
            }
        ),
        500,
    )


from .dynamic_configuration import routes as routes  # noqa E402
