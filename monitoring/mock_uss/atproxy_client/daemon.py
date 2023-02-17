import json
from datetime import timedelta, datetime
import time
from typing import Tuple, Optional

from loguru import logger
import requests
from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    ClearAreaRequest,
)

from implicitdict import ImplicitDict
from monitoring import mock_uss
from monitoring.atproxy.requests import (
    RequestType,
    SCDInjectionPutFlightRequest,
    SCDInjectionDeleteFlightRequest,
    SCDInjectionClearAreaRequest,
    SCD_REQUESTS,
)
from monitoring.atproxy.handling import (
    ListQueriesResponse,
    PutQueryRequest,
    PendingRequest,
)
from monitoring.mock_uss.atproxy_client import config
from monitoring.mock_uss import webapp
from monitoring.mock_uss.scdsc.routes_injection import (
    injection_status,
    scd_capabilities,
    inject_flight,
    delete_flight,
    clear_area,
)
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    InjectFlightRequest,
)

from monitoring.monitorlib import fetch

TASK_POLL_ATPROXY = "poll atproxy"
MAX_DAEMON_PROCESSES = 1
ATPROXY_WAIT_TIMEOUT = timedelta(minutes=5)


@webapp.setup_task("verify atproxy connectivity")
def _wait_for_atproxy() -> None:
    """Wait for atproxy to be available"""
    base_url = mock_uss.webapp.config[config.KEY_ATPROXY_BASE_URL]
    basic_auth = mock_uss.webapp.config[config.KEY_ATPROXY_BASIC_AUTH].tuple
    timeout = datetime.utcnow() + ATPROXY_WAIT_TIMEOUT
    status_url = f"{base_url}/status"
    while not webapp.is_stopping():
        resp = None
        try:
            resp = requests.get(status_url, auth=basic_auth)
            if resp.status_code == 200:
                break
            logger.info(
                "atproxy at {} is not yet ready; received {} at /status: {}",
                base_url,
                resp.status_code,
                resp.content.decode(),
            )
        except requests.exceptions.ConnectionError as e:
            logger.info("atproxy at {} is not yet reachable: {}", base_url, str(e))
        if datetime.utcnow() > timeout:
            raise RuntimeError(
                f"Timeout while trying to connect to atproxy at {status_url}; latest attempt yielded {resp.status_code if resp else 'ConnectionError'}"
            )
        time.sleep(5)

    # Enable polling
    webapp.set_task_period(TASK_POLL_ATPROXY, timedelta(seconds=0))


@webapp.periodic_task(TASK_POLL_ATPROXY)
def _poll_atproxy() -> None:
    """Poll atproxy for new requests and handle any unhandled requests"""
    base_url = mock_uss.webapp.config[config.KEY_ATPROXY_BASE_URL]
    query_url = f"{base_url}/handler/queries"
    basic_auth = mock_uss.webapp.config[config.KEY_ATPROXY_BASIC_AUTH].tuple

    # Poll atproxy to see if there are any requests pending
    query = fetch.query_and_describe(None, "GET", query_url, auth=basic_auth)
    if query.status_code != 200:
        logger.error(
            "Error {} polling {}:\n{}",
            query.status_code,
            query_url,
            "JSON: " + json.dumps(query.response.json, indent=2)
            if query.response.json
            else f"Body: {query.response.content}",
        )
        time.sleep(5)
        return
    try:
        queries_resp: ListQueriesResponse = ImplicitDict.parse(
            query.response.json, ListQueriesResponse
        )
    except ValueError as e:
        logger.error(
            "Error parsing atproxy response to request for queries: {}", str(e)
        )
        time.sleep(5)
        return
    if not queries_resp.requests:
        logger.debug("No queries currently pending.")
        return

    # Identify a request to handle
    request_to_handle = queries_resp.requests[0]

    # Handle the request
    logger.info(
        "Handling {} request, id {}", request_to_handle.type, request_to_handle.id
    )
    fulfillment = PutQueryRequest(
        return_code=500,
        response={"message": "Unknown error in mock_uss atproxy client handler"},
    )
    try:
        content, code = _fulfill_request(request_to_handle)
        logger.info(f"Request {request_to_handle.id} fulfillment has code {code}")
        fulfillment = PutQueryRequest(return_code=code, response=content)
    except ValueError as e:
        msg = f"mock_uss atproxy client handler encountered ValueError: {e}"
        logger.error(msg)
        fulfillment = PutQueryRequest(
            return_code=400,
            response={"message": msg},
        )
    except NotImplementedError as e:
        msg = f"mock_uss atproxy client handler encountered NotImplementedError: {e}"
        logger.error(msg)
        fulfillment = PutQueryRequest(
            return_code=500,
            response={"message": msg},
        )
    finally:
        for attempt in range(1, 4):
            query = fetch.query_and_describe(
                None,
                "PUT",
                f"{query_url}/{request_to_handle.id}",
                json=fulfillment,
                auth=basic_auth,
            )
            if query.status_code != 204:
                logger.error(
                    "Error {} reporting response {} to query {} on attempt {}; details:\n{}",
                    query.status_code,
                    fulfillment.return_code,
                    request_to_handle.id,
                    attempt,
                    "JSON: " + json.dumps(query.response.json, indent=2)
                    if query.response.json
                    else f"Body: {query.response.content}",
                )
                logger.debug(
                    "Query details for failed attempt to report response to atproxy:\n{}",
                    json.dumps(query, indent=2),
                )
            else:
                logger.info(
                    f"Delivered response to request {request_to_handle.id} to atproxy on attempt {attempt}"
                )
                break


def _fulfill_request(request_to_handle: PendingRequest) -> Tuple[Optional[dict], int]:
    """Fulfill a PendingRequest from atproxy by invoking appropriate handler logic

    Args:
        request_to_handle: PendingRequest to handle

    Returns:
        * dict content of response, or None for no response JSON body
        * HTTP status code of response
    """
    req_type = request_to_handle.type

    if req_type in SCD_REQUESTS:
        if mock_uss.SERVICE_SCDSC not in mock_uss.enabled_services:
            raise ValueError(
                f"mock_uss cannot handle {req_type} request because {mock_uss.SERVICE_SCDSC} is not one of the enabled services ({', '.join(mock_uss.enabled_services)})"
            )

    if req_type == RequestType.SCD_GetStatus:
        return injection_status()
    elif req_type == RequestType.SCD_GetCapabilities:
        return scd_capabilities()
    elif req_type == RequestType.SCD_PutFlight:
        req = ImplicitDict.parse(
            request_to_handle.request, SCDInjectionPutFlightRequest
        )
        body = ImplicitDict.parse(req.request_body, InjectFlightRequest)
        return inject_flight(req.flight_id, body)
    elif req_type == RequestType.SCD_DeleteFlight:
        req = ImplicitDict.parse(
            request_to_handle.request, SCDInjectionDeleteFlightRequest
        )
        return delete_flight(req.flight_id)
    elif req_type == RequestType.SCD_CreateClearAreaRequest:
        req = ImplicitDict.parse(
            request_to_handle.request, SCDInjectionClearAreaRequest
        )
        body = ImplicitDict.parse(req.request_body, ClearAreaRequest)
        return clear_area(body)
    else:
        # TODO: Add RID injection & observation support
        raise NotImplementedError(f"Unsupported request type: {request_to_handle.type}")
