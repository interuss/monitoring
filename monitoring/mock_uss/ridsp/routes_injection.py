import datetime
import uuid

import arrow
import flask
from implicitdict import ImplicitDict
from loguru import logger
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    OPERATIONS,
    ChangeTestResponse,
    OperationID,
    QueryUserNotificationsResponse,
)

from monitoring.mock_uss.app import require_config_value, webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.config import KEY_BASE_URL
from monitoring.mock_uss.riddp.config import KEY_RID_VERSION
from monitoring.mock_uss.ridsp import utm_client
from monitoring.monitorlib import geo
from monitoring.monitorlib.idempotency import idempotent_request
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.rid_automated_testing import injection_api

from . import database
from .database import db

require_config_value(KEY_BASE_URL)
require_config_value(KEY_RID_VERSION)

# Time after the last position report during which the created ISA will still
# exist.  This value must be at least 60 seconds per NET0610.
RECENT_POSITIONS_BUFFER = datetime.timedelta(seconds=60.2)


class ErrorResponse(ImplicitDict):
    message: str


@webapp.route("/ridsp/injection/tests/<test_id>", methods=["PUT"])
@requires_scope(injection_api.SCOPE_RID_QUALIFIER_INJECT)
@idempotent_request()
def ridsp_create_test(test_id: str) -> tuple[str | flask.Response, int]:
    """Implements test creation in RID automated testing injection API."""
    logger.info(f"Create test {test_id}")
    rid_version = webapp.config[KEY_RID_VERSION]
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req_body: injection_api.CreateTestParameters = ImplicitDict.parse(
            json, injection_api.CreateTestParameters
        )
        record = database.TestRecord(
            version=str(uuid.uuid4()), flights=req_body.requested_flights
        )
    except ValueError as e:
        msg = f"Create test {test_id} unable to parse JSON: {e}"
        return msg, 400

    # Create ISA in DSS
    (t0, t1) = req_body.get_span()
    t1 += RECENT_POSITIONS_BUFFER
    rect = req_body.get_rect()
    if rid_version == RIDVersion.f3411_19:
        uss_base_url = f"{webapp.config[KEY_BASE_URL]}/mock/ridsp"
    elif rid_version == RIDVersion.f3411_22a:
        uss_base_url = f"{webapp.config[KEY_BASE_URL]}/mock/ridsp/v2"
    else:
        raise NotImplementedError(
            f"Unable to determine base URL for RID version {rid_version}"
        )
    mutated_isa = mutate.put_isa(
        area_vertices=geo.get_latlngrect_vertices(rect),
        alt_lo=0,
        alt_hi=3048,
        start_time=t0,
        end_time=t1,
        uss_base_url=uss_base_url,
        isa_id=record.version,
        rid_version=rid_version,
        utm_client=utm_client,
    )
    if not mutated_isa.dss_query.success:
        errors = "\n".join(mutated_isa.dss_query.errors)
        msg = f"Unable to create ISA in DSS ({mutated_isa.dss_query.status_code}): {errors}"
        logger.error(msg)
        response = ErrorResponse(message=msg)
        response["errors"] = mutated_isa.dss_query.errors
        response["dss_query"] = mutated_isa.dss_query
        return flask.jsonify(response), 412
    bounds = f"(lat {rect.lat_lo().degrees}, lng {rect.lng_lo().degrees})-(lat {rect.lat_hi().degrees}, lng {rect.lng_hi().degrees})"
    isa = mutated_isa.dss_query.isa
    logger.info(
        f"Created ISA {isa.id} version {isa.version} from {t0} to {t1} at {bounds}"
    )
    record.isa_version = mutated_isa.dss_query.isa.version
    for url, notification in mutated_isa.notifications.items():
        code = notification.query.status_code
        if code == 200:
            logger.warning(
                f"Notification to {notification.query.request.url} incorrectly returned 200 rather than 204"
            )
        elif code != 204:
            msg = f"Notification failure {code} to {notification.query.request.url}"
            logger.error(msg)
            response = ErrorResponse(message=msg)
            response["query"] = notification.query
            return flask.jsonify(response), 412

    with db.transact() as tx:
        tx.value.tests[test_id] = record
        tx.value.notifications.create_notifications_if_needed(record)

    return flask.jsonify(
        ChangeTestResponse(version=record.version, injected_flights=record.flights)
    ), 200


@webapp.route("/ridsp/injection/tests/<test_id>/<version>", methods=["DELETE"])
@requires_scope(injection_api.SCOPE_RID_QUALIFIER_INJECT)
def ridsp_delete_test(test_id: str, version: str) -> tuple[str | flask.Response, int]:
    """Implements test deletion in RID automated testing injection API."""
    logger.info(f"Delete test {test_id}")
    rid_version = webapp.config[KEY_RID_VERSION]
    record = db.value.tests.get(test_id, None)

    if record is None:
        return f'Test "{test_id}" not found', 404

    if record.version != version:
        return (
            f'Test "{test_id}" has version "{record.version}" rather than the specified version "{version}"',
            404,
        )

    result = ChangeTestResponse(version=record.version, injected_flights=record.flights)

    if record.isa_version is not None:
        # Delete ISA from DSS
        deleted_isa = mutate.delete_isa(
            isa_id=record.version,
            isa_version=record.isa_version,
            rid_version=rid_version,
            utm_client=utm_client,
        )
        if not deleted_isa.dss_query.success:
            logger.error(f"Unable to delete ISA {record.version} from DSS")
            response = ErrorResponse(message="Unable to delete ISA from DSS")
            response["errors"] = deleted_isa.dss_query.errors
            response["query"] = deleted_isa.dss_query
            return flask.jsonify(response), 412
        logger.info(f"Deleted ISA {deleted_isa.dss_query.isa.id}")

        for url, notification in deleted_isa.notifications.items():
            code = notification.query.status_code
            if code == 200:
                logger.warning(
                    f"Notification to {notification.query.request.url} incorrectly returned 200 rather than 204"
                )
            elif code != 204:
                logger.error(
                    f"Notification failure {code} to {notification.query.request.url}"
                )
                result["query"] = notification.query

    with db.transact() as tx:
        del tx.value.tests[test_id]
    return flask.jsonify(result), 200


@webapp.route(
    f"/ridsp/injection{OPERATIONS[OperationID.QueryUserNotifications].path}",
    methods=["GET"],
)
@requires_scope(injection_api.SCOPE_RID_QUALIFIER_INJECT)
def ridsp_get_user_notifications() -> tuple[str | flask.Response, int]:
    """Returns the list of user notifications observed by the virtual user"""

    if "after" not in flask.request.args:
        return (
            flask.jsonify(ErrorResponse(message='Missing required "after" parameter')),
            400,
        )
    try:
        after = arrow.get(flask.request.args["after"])
    except ValueError as e:
        return (
            flask.jsonify(ErrorResponse(message=f"Error parsing after: {e}")),
            400,
        )

    if "before" not in flask.request.args:
        before = arrow.utcnow()
    else:
        try:
            before = arrow.get(flask.request.args["before"])
        except ValueError as e:
            return (
                flask.jsonify(ErrorResponse(message=f"Error parsing before: {e}")),
                400,
            )

    if before < after:
        return (
            flask.jsonify(
                ErrorResponse(message=f"'Before' ({before}) is after 'after' ({after})")
            ),
            400,
        )

    final_list = []

    for user_notification in db.value.notifications.user_notifications:
        if (
            after.datetime
            <= user_notification.observed_at.value.datetime
            <= before.datetime
        ):
            final_list.append(user_notification)

    r = QueryUserNotificationsResponse(user_notifications=final_list)

    return flask.jsonify(r), 200
