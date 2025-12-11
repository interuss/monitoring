import flask
from uas_standards.interuss.automated_testing.versioning import api, constants

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.monitorlib import versioning


@webapp.route("/versioning/versions/<system_identity>", methods=["GET"])
@requires_scope(constants.Scope.ReadSystemVersions)
def versioning_get_version(system_identity: str) -> flask.Response:
    version = versioning.get_code_version()
    return flask.jsonify(
        api.GetVersionResponse(
            system_identity=api.SystemBoundaryIdentifier(system_identity),
            system_version=api.VersionIdentifier(version),
        )
    )
