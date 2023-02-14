import datetime
from typing import Tuple
import uuid

import flask
from loguru import logger

from uas_standards.astm.f3411.v19.api import ErrorResponse
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.rid_automated_testing import injection_api
from implicitdict import ImplicitDict
from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss import config, resources
from uas_standards.interuss.automated_testing.rid.v1.injection import ChangeTestResponse
from . import database
from .database import db


# Time after the last position report during which the created ISA will still
# exist.  This value must be at least 60 seconds per NET0610.
from ...monitorlib.rid import RIDVersion

RECENT_POSITIONS_BUFFER = datetime.timedelta(seconds=60.2)


@webapp.route("/ridsp/injection/tests/<test_id>", methods=["PUT"])
@requires_scope([injection_api.SCOPE_RID_QUALIFIER_INJECT])
def ridsp_create_test(test_id: str) -> Tuple[str, int]:
    """Implements test creation in RID automated testing injection API."""
    logger.info(f"Create test {test_id}")
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
        msg = "Create test {} unable to parse JSON: {}".format(test_id, e)
        return msg, 400

    # Create ISA in DSS
    (t0, t1) = req_body.get_span()
    t1 += RECENT_POSITIONS_BUFFER
    rect = req_body.get_rect()
    uss_base_url = "{}/mock/ridsp".format(webapp.config.get(config.KEY_BASE_URL))
    mutated_isa = mutate.put_isa(
        area=rect,
        start_time=t0,
        end_time=t1,
        uss_base_url=uss_base_url,
        isa_id=record.version,
        rid_version=RIDVersion.f3411_19,
        utm_client=resources.utm_client,
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
    for (url, notification) in mutated_isa.notifications.items():
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

    with db as tx:
        tx.tests[test_id] = record
    return flask.jsonify(
        ChangeTestResponse(version=record.version, injected_flights=record.flights)
    )


@webapp.route("/ridsp/injection/tests/<test_id>", methods=["DELETE"])
@requires_scope([injection_api.SCOPE_RID_QUALIFIER_INJECT])
def ridsp_delete_test(test_id: str) -> Tuple[str, int]:
    """Implements test deletion in RID automated testing injection API."""
    logger.info(f"Delete test {test_id}")
    record = db.value.tests.get(test_id, None)

    if record is None:
        return 'Test "{}" not found'.format(test_id), 404

    # Delete ISA from DSS
    deleted_isa = mutate.delete_isa(
        isa_id=record.version,
        isa_version=record.isa_version,
        rid_version=RIDVersion.f3411_19,
        utm_client=resources.utm_client,
    )
    if not deleted_isa.dss_query.success:
        logger.error(f"Unable to delete ISA {record.version} from DSS")
        response = ErrorResponse(message="Unable to delete ISA from DSS")
        response["errors"] = deleted_isa.dss_query.errors
        return flask.jsonify(response), 412
    logger.info(f"Created ISA {deleted_isa.dss_query.isa.id}")
    result = ChangeTestResponse(version=record.version, injected_flights=record.flights)
    for (url, notification) in deleted_isa.notifications.items():
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

    with db as tx:
        del tx.tests[test_id]
    return flask.jsonify(result)
