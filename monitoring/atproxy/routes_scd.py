from datetime import timedelta
from typing import Tuple

import flask
from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightRequest,
    ClearAreaRequest,
)

from . import handling
from .app import webapp
from .config import KEY_QUERY_TIMEOUT
from .oauth import requires_scope
from .requests import (
    SCDInjectionStatusRequest,
    SCDInjectionCapabilitiesRequest,
    SCDInjectionPutFlightRequest,
    SCDInjectionDeleteFlightRequest,
    SCDInjectionClearAreaRequest,
)
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    SCOPE_SCD_QUALIFIER_INJECT,
)


timeout = timedelta(seconds=webapp.config[KEY_QUERY_TIMEOUT])


@webapp.route("/scd/v1/status", methods=["GET"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def scd_injection_status() -> Tuple[str, int]:
    """Implements status in SCD automated testing injection API."""
    return handling.fulfill_query(SCDInjectionStatusRequest(), timeout)


@webapp.route("/scd/v1/capabilities", methods=["GET"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def scd_injection_capabilities() -> Tuple[str, int]:
    """Implements capabilities in SCD automated testing injection API."""
    return handling.fulfill_query(SCDInjectionCapabilitiesRequest(), timeout)


@webapp.route("/scd/v1/flights/<flight_id>", methods=["PUT"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def scd_injection_put_flight(flight_id: str) -> Tuple[str, int]:
    """Implements PUT flight in SCD automated testing injection API."""
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req_body: InjectFlightRequest = ImplicitDict.parse(json, InjectFlightRequest)
    except ValueError as e:
        msg = "Upsert flight {} unable to parse JSON: {}".format(flight_id, e)
        return msg, 400
    return handling.fulfill_query(
        SCDInjectionPutFlightRequest(flight_id=flight_id, request_body=req_body),
        timeout,
    )


@webapp.route("/scd/v1/flights/<flight_id>", methods=["DELETE"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def scd_injection_delete_flight(flight_id: str) -> Tuple[str, int]:
    """Implements flight deletion in SCD automated testing injection API."""
    return handling.fulfill_query(
        SCDInjectionDeleteFlightRequest(flight_id=flight_id), timeout
    )


@webapp.route("/scd/v1/clear_area_requests", methods=["POST"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def scd_injection_clear_area() -> Tuple[str, int]:
    """Implements area clearing in RID automated testing injection API."""
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req_body: ClearAreaRequest = ImplicitDict.parse(json, ClearAreaRequest)
    except ValueError as e:
        msg = "Clear area request unable to parse JSON: {}".format(e)
        return msg, 400

    return handling.fulfill_query(
        SCDInjectionClearAreaRequest(request_body=req_body), timeout
    )
