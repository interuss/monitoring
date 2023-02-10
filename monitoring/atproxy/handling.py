import os
from datetime import datetime, timedelta
import time
from typing import Tuple, List, Optional
import uuid

import flask
from loguru import logger

from implicitdict import ImplicitDict
from .database import db, Query, QueryState


class PendingRequest(ImplicitDict):
    """A pending query the handler client is expected to handle."""

    id: str
    """ID of the query; used to PUT /handler/queries/<id> the result."""

    type: str
    """Type of query -- matches a request_type_name() in requests.py."""

    request: dict
    """All relevant information about the request in the *Request descriptor from requests.py matching `type`."""


class ListQueriesResponse(ImplicitDict):
    """Response body schema for GET /handler/queries."""

    requests: List[PendingRequest]
    """All of the queries available for the handler client to handle."""


class PutQueryRequest(ImplicitDict):
    """Request body schema for PUT /handler/queries/<id>."""

    response: Optional[dict] = None
    """JSON body of the response, or None for no JSON body."""

    return_code: int
    """HTTP return code."""


def fulfill_query(req: ImplicitDict) -> Tuple[str, int]:
    """Fulfill an incoming automated testing query.

    :param req: Request descriptor from requests.py.
    :return: Flask endpoint handler result (content, HTTP code).
    """
    t_start = datetime.utcnow()
    query = Query(type=req.request_type_name(), request=req)
    timeout = timedelta(seconds=59)
    id = str(uuid.uuid4())
    logger.debug('Attempting to fulfill {} query {} from worker {}', query.type, id, os.getpid())

    # Add query to be handled to the set of handleable queries
    with db as tx:
        tx.queries[id] = query
        logger.debug('Added {} query {} to handler queue'.format(query.type, id))

    # Frequently check if the query has been fulfilled
    while datetime.utcnow() < t_start + timeout:
        time.sleep(0.1)
        with db as tx:
            if tx.queries[id].state == QueryState.Complete:
                # Query was successfully fulfilled; return the result
                logger.debug('Fulfilling {} query {}'.format(query.type, id))
                query = tx.queries.pop(id)
                logger.debug('Fulfilled {} query {} with {} from worker {}', query.type, id, query.return_code, os.getpid())
                if query.response is not None:
                    return flask.jsonify(query.response), query.return_code
                else:
                    return '', query.return_code

    # Time expired; remove request from queue and indicate error
    with db as tx:
        tx.queries.pop(id)
    logger.debug('Failed to fulfill {} query {} in time (backend handler did not provide a response) from worker {}', query.type, id, os.getpid())
    return flask.jsonify({'message': 'Backend handler did not respond within the alotted time'}), 500
