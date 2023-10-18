import base64
import hashlib
from functools import wraps
import json
from typing import Callable, Optional, Dict

import arrow
import flask
from loguru import logger

from implicitdict import ImplicitDict, StringBasedDateTime
from monitoring.monitorlib.multiprocessing import SynchronizedValue


_max_request_buffer_size = int(10e6)
"""Number of bytes to dedicate to caching responses"""


class Response(ImplicitDict):
    """Information about a previously-returned response.

    Note that this object is never actually used (in order to maximize performance); instead it serves as documentation
    of the structure of the fields within a plain JSON dict/object."""

    json: Optional[dict]
    body: Optional[str]
    code: int
    timestamp: StringBasedDateTime


def _get_responses(raw: bytes) -> Dict[str, Response]:
    return json.loads(raw.decode("utf-8"))


def _set_responses(responses: Dict[str, Response]) -> bytes:
    while True:
        s = json.dumps(responses)
        if len(s) <= _max_request_buffer_size:
            break

        # Remove oldest cached response
        oldest_id = None
        oldest_timestamp = None
        for request_id, response in responses.items():
            t = arrow.get(response["timestamp"])
            if oldest_timestamp is None or t < oldest_timestamp:
                oldest_id = request_id
                oldest_timestamp = t

        del responses[oldest_id]
    return s.encode("utf-8")


_fulfilled_requests = SynchronizedValue(
    {},
    decoder=_get_responses,
    encoder=_set_responses,
    capacity_bytes=_max_request_buffer_size,
)


def get_hashed_request_id() -> Optional[str]:
    """Retrieves an identifier for the request by hashing key characteristics of the request."""
    characteristics = flask.request.method + flask.request.url
    if flask.request.json:
        characteristics += json.dumps(flask.request.json)
    else:
        characteristics += flask.request.data.decode("utf-8")
    return base64.b64encode(
        hashlib.sha512(characteristics.encode("utf-8")).digest()
    ).decode("utf-8")


def idempotent_request(get_request_id: Optional[Callable[[], Optional[str]]] = None):
    """Decorator for idempotent Flask view handlers.

    When subsequent requests are received with the same request identifier, this decorator will use a recent cached
    response instead of invoking the underlying handler when possible.  Note that there is no verification that the rest
    of the request (apart from the request ID) is identical, so a request with different content but the same request ID
    will receive the cached response from the first request.  A developer could compute a request ID based on a hash of
    important request characteristics to control this behavior.

    Note that cached response characteristics are limited and the full original response is not produced verbatim.
    """
    if get_request_id is None:
        get_request_id = get_hashed_request_id

    def outer_wrapper(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            request_id = get_request_id()

            cached_requests = _fulfilled_requests.value
            if request_id in cached_requests:
                endpoint = (
                    flask.request.url_rule.rule
                    if flask.request.url_rule is not None
                    else "unknown endpoint"
                )
                logger.warning(
                    "Fulfilling {} {} with cached response for request {}",
                    flask.request.method,
                    endpoint,
                    request_id,
                )
                response = cached_requests[request_id]
                if response["body"] is not None:
                    return response["body"], response["code"]
                else:
                    return flask.jsonify(response["json"]), response["code"]

            result = fn(*args, **kwargs)

            response = {
                "timestamp": arrow.utcnow().isoformat(),
                "code": 200,
                "body": None,
                "json": None,
            }
            keep_code = False
            if isinstance(result, tuple):
                if len(result) == 2:
                    if not isinstance(result[1], int):
                        raise NotImplementedError(
                            f"Unable to cache Flask view handler result where the second 2-tuple element is a '{type(result[1]).__name__}'"
                        )
                    response["code"] = result[1]
                    keep_code = True
                    result = result[0]
                else:
                    raise NotImplementedError(
                        f"Unable to cache Flask view handler result which is a tuple of ({', '.join(type(v).__name__ for v in result)})"
                    )

            if isinstance(result, str):
                response["body"] = result
                response["json"] = None
            elif isinstance(result, flask.Response):
                try:
                    response["json"] = result.get_json()
                except ValueError:
                    response["body"] = result.get_data(as_text=True)
                if not keep_code:
                    response["code"] = result.status_code
            else:
                raise NotImplementedError(
                    f"Unable to cache Flask view handler result of type '{type(result).__name__}'"
                )

            with _fulfilled_requests as cached_requests:
                cached_requests[request_id] = response

            return result

        return wrapper

    return outer_wrapper
