import flask
from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.geospatial_map.v1.api import (
    OPERATIONS,
    GeospatialMapCheckResult,
    GeospatialMapCheckResultFeaturesSelectionOutcome,
    GeospatialMapQueryReply,
    GeospatialMapQueryRequest,
    OperationID,
)
from uas_standards.interuss.automated_testing.geospatial_map.v1.constants import Scope

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.auth import requires_scope


def geospatial_map_route(op_id: OperationID):
    op = OPERATIONS[op_id]
    flask_url = op.path.replace("{", "<").replace("}", ">")
    return webapp.route("/geospatial_map/v1" + flask_url, methods=[op.verb])


@geospatial_map_route(OperationID.GetStatus)
@requires_scope(Scope.DirectAutomatedTest)
def geospatial_map_status():
    raise NotImplementedError()


@geospatial_map_route(OperationID.PutGeospatialDataSource)
@requires_scope(Scope.DirectAutomatedTest)
def geospatial_map_put_data_source(geospatial_data_source_id: str):
    raise NotImplementedError()


@geospatial_map_route(OperationID.GetGeospatialDataSourceStatus)
@requires_scope(Scope.DirectAutomatedTest)
def geospatial_map_get_data_source_status(geospatial_data_source_id: str):
    raise NotImplementedError()


@geospatial_map_route(OperationID.ListGeospatialDataSources)
@requires_scope(Scope.DirectAutomatedTest)
def geospatial_map_list_data_sources():
    raise NotImplementedError()


@geospatial_map_route(OperationID.QueryGeospatialMap)
@requires_scope(Scope.Query)
def geospatial_map_query():
    try:
        req: GeospatialMapQueryRequest = ImplicitDict.parse(
            flask.request.json, GeospatialMapQueryRequest
        )
    except ValueError as e:
        return (
            flask.jsonify(
                {"error": f"Could not parse GeospatialMapQueryRequest: {str(e)}"}
            ),
            400,
        )

    results = []
    for _ in req.checks:
        # TODO: Actually evaluate check (always returns Present currently)
        results.append(
            GeospatialMapCheckResult(
                features_selection_outcome=GeospatialMapCheckResultFeaturesSelectionOutcome.Present
            )
        )

    return GeospatialMapQueryReply(results=results)
