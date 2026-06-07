import asyncio
import copy
from datetime import UTC, datetime
import json
import os
import uuid

import aiohttp
from loguru import logger

from implicitdict import StringBasedDateTime
from monitoring.monitorlib import infrastructure
from monitoring.monitorlib.fetch import (
    RequestDescription,
    ResponseDescription,
    describe_aiohttp_response,
    describe_failed_aiohttp_response,
    get_traceback_location,
    is_fake_netloc,
    settings,
    Query,
    QueryType,
)


async def query_and_describe(
    client: infrastructure.AsyncUTMTestSession,
    verb: str,
    url: str,
    query_type: QueryType | None = None,
    participant_id: str | None = None,
    expect_failure: bool = False,
    **kwargs,
) -> Query:
    """Attempt to perform an asynchronous query, and then describe the results of that attempt.

    This function is equivalent to fetch.query_and_describe, but for an AsyncUTMTestSession.
    """
    req_kwargs = kwargs.copy()
    if "timeout" not in req_kwargs:
        req_kwargs["timeout"] = client.timeout_seconds

    # Attach a request_id field to the JSON body of any outgoing request with a JSON body that doesn't already have one
    if (
        settings.add_request_id
        and "json" in req_kwargs
        and isinstance(req_kwargs["json"], dict)
        and "request_id" not in req_kwargs["json"]
    ):
        json_body = json.loads(json.dumps(req_kwargs["json"]))
        json_body["request_id"] = str(uuid.uuid4())
        req_kwargs["json"] = json_body

    failures = []
    is_netloc_fake = is_fake_netloc(url)
    previous_query = None

    prefixed_url = client._prefix_url + url if url.startswith("/") else url

    # Adjust request kwargs for description building (gets auth headers, etc.)
    desc_kwargs = copy.deepcopy(req_kwargs)
    desc_kwargs = client.adjust_request_kwargs(prefixed_url, verb, desc_kwargs)

    def build_failing_query(t0: datetime) -> Query:
        t1 = datetime.now(UTC)
        req_descr = RequestDescription(
            method=verb,
            url=prefixed_url,
            headers=desc_kwargs.get("headers", {}),
            json=desc_kwargs.get("json"),
            body=desc_kwargs.get("data"),
            initiated_at=StringBasedDateTime(t0),
        )
        query = Query(
            request=req_descr,
            response=ResponseDescription(
                code=None,
                failure="\n".join(failures),
                elapsed_s=(t1 - t0).total_seconds(),
                reported=StringBasedDateTime(t1),
            ),
            participant_id=participant_id,
            _previous_query=previous_query,
        )
        if query_type is not None:
            query.query_type = query_type
        return query

    # Choose HTTP method function
    verb_upper = verb.upper()
    if verb_upper == "GET":
        request_func = client.get
    elif verb_upper == "PUT":
        request_func = client.put
    elif verb_upper == "POST":
        request_func = client.post
    elif verb_upper == "DELETE":
        request_func = client.delete
    else:
        raise ValueError(f"Unsupported HTTP verb: {verb}")

    for attempt in range(settings.attempts):
        t0 = datetime.now(UTC)
        try:
            if is_netloc_fake:
                failure_message = f"query_and_describe attempt {attempt + 1} from PID {os.getpid()} to {verb} {url} was not attempted because network location of {url} was identified as fake: {settings.fake_netlocs}\nAt {get_traceback_location()}"
                failures.append(failure_message)
                return build_failing_query(t0)

            status, headers, resp_json = await request_func(url, **req_kwargs)
            t1 = datetime.now(UTC)
            duration = t1 - t0

            req_descr = RequestDescription(
                method=verb,
                url=prefixed_url,
                headers=desc_kwargs.get("headers", {}),
                json=desc_kwargs.get("json"),
                body=desc_kwargs.get("data"),
                initiated_at=StringBasedDateTime(t0),
            )
            response = describe_aiohttp_response(
                status, headers, resp_json, duration
            )
            query = Query(
                request=req_descr,
                response=response,
                participant_id=participant_id,
                _previous_query=previous_query,
            )
            if query_type is not None:
                query.query_type = query_type
            return query

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            t1 = datetime.now(UTC)
            duration = t1 - t0
            failure_message = f"query_and_describe attempt {attempt + 1} from PID {os.getpid()} to {verb} {url} failed with exception {type(e).__name__}: {str(e)}\nAt {get_traceback_location()}"
            if not expect_failure:
                logger.warning(failure_message)
            failures.append(failure_message)

            retryable = True
            if isinstance(e, aiohttp.ClientError) and not isinstance(
                e,
                (
                    aiohttp.ServerConnectionError,
                    aiohttp.ClientPayloadError,
                    aiohttp.ClientConnectorError,
                ),
            ):
                retryable = False

            if not retryable:
                return build_failing_query(t0)

        previous_query = build_failing_query(t0)

    if not previous_query:
        raise Exception(
            "Internal error: arrived after retried without any expected failed query"
        )

    return previous_query
