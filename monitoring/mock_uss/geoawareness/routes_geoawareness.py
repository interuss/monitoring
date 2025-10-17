import flask
from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.geo_awareness.v1.api import (
    CreateGeozoneSourceRequest,
    GeozonesCheckReply,
    GeozonesCheckRequest,
)

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.geoawareness.check import check_geozones
from monitoring.mock_uss.geoawareness.geozone_sources import (
    create_geozone_source,
    delete_geozone_source,
    get_geozone_source,
)
from monitoring.monitorlib.geoawareness_automated_testing.api import (
    SCOPE_GEOAWARENESS_TEST,
)


@webapp.route(
    "/geoawareness/geozone_sources/<geozone_source_id>",
    methods=["GET"],
)
@requires_scope(SCOPE_GEOAWARENESS_TEST)
def geoawareness_get_geozone_sources(
    geozone_source_id: str,
) -> tuple[flask.Response | str, int]:
    return get_geozone_source(geozone_source_id)


@webapp.route(
    "/geoawareness/geozone_sources/<geozone_source_id>",
    methods=["PUT"],
)
@requires_scope(SCOPE_GEOAWARENESS_TEST)
def geoawareness_put_geozone_sources(
    geozone_source_id: str,
) -> tuple[flask.Response | str, int]:
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        body: CreateGeozoneSourceRequest = ImplicitDict.parse(
            json, CreateGeozoneSourceRequest
        )
    except ValueError as e:
        msg = f"Create geozone source {geozone_source_id} unable to parse JSON: {e}"
        return msg, 400

    return create_geozone_source(geozone_source_id, body)


@webapp.route(
    "/geoawareness/geozone_sources/<geozone_source_id>",
    methods=["DELETE"],
)
@requires_scope(SCOPE_GEOAWARENESS_TEST)
def geoawareness_delete_geozone_sources(
    geozone_source_id: str,
) -> tuple[flask.Response | str, int]:
    return delete_geozone_source(geozone_source_id)


@webapp.route("/geoawareness/check", methods=["POST"])
@requires_scope(SCOPE_GEOAWARENESS_TEST)
def geoawareness_check():
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        body: GeozonesCheckRequest = ImplicitDict.parse(json, GeozonesCheckRequest)
    except ValueError as e:
        msg = f"Geozone check unable to parse JSON: {e}"
        return msg, 400
    applicable_geozone = check_geozones(body)

    return GeozonesCheckReply(applicableGeozone=applicable_geozone), 200
