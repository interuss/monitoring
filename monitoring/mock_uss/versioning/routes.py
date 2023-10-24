from typing import Tuple

import flask

from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.monitorlib import versioning
from uas_standards.interuss.automated_testing.versioning import api, constants


@webapp.route("/versioning/versions/<system_identity>", methods=["GET"])
@requires_scope(constants.Scope.ReadSystemVersions)
def versioning_get_version(system_identity: str) -> Tuple[str, int]:
    version = versioning.get_code_version()
    return flask.jsonify(
        api.GetVersionResponse(
            system_identity=api.SystemBoundaryIdentifier(system_identity),
            system_version=api.VersionIdentifier(version),
        )
    )
