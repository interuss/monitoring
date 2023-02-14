import os
from datetime import datetime, timedelta
import time
from typing import Tuple

import flask
from loguru import logger

from implicitdict import ImplicitDict
from .app import webapp, basic_auth
from .database import db, Query, QueryState
from .handling import ListQueriesResponse, PendingRequest, PutQueryRequest


@webapp.route('/handler/queries', methods=['GET'])
@basic_auth.login_required
def list_queries() -> Tuple[str, int]:
    """Lists outstanding queries to be handled.

    See ListQueriesResponse for response body schema.
    """
    t_start = datetime.utcnow()
    logger.debug('Handler requesting queries from worker {}', os.getpid())
    max_timeout = timedelta(seconds=5)
    while datetime.utcnow() < t_start + max_timeout:
        with db as tx:
            response = ListQueriesResponse(requests=[
                PendingRequest(id=id, type=q.type, request=q.request)
                for id, q in tx.queries.items()
                if q.state == QueryState.Queued])
            if response.requests:
                logger.debug('Provided handler {} queries'.format(len(response.requests)))
                return flask.jsonify(response)
        time.sleep(0.1)
    logger.debug('No queries available for handler from worker {}', os.getpid())
    return flask.jsonify(ListQueriesResponse(requests=[]))


@webapp.route('/handler/queries/<id>', methods=['PUT'])
@basic_auth.login_required
def put_query_result(id: str) -> Tuple[str, int]:
    """Fulfills an outstanding query.

    See PutQueryRequest for request body schema.
    """
    logger.debug('Handler instructed to fulfill request {} from worker {}', id, os.getpid())
    try:
        request: PutQueryRequest = ImplicitDict.parse(flask.request.json, PutQueryRequest)
    except ValueError as e:
        msg = f'Could not parse PutQueryRequest due to {type(e).__name__} on worker {os.getpid()}: {str(e)}'
        logger.error(msg)
        return flask.jsonify({'message': msg}), 400
    with db as tx:
        if id not in tx.queries:
            msg = f'No outstanding request with ID {id} exists on worker {os.getpid()}'
            logger.error(msg)
            return flask.jsonify({'message': msg}), 400
        query: Query = tx.queries[id]
        logger.debug('{} query {} handled with code {}', query.type, id, request.return_code)
        query.return_code = request.return_code
        query.response = request.response
        query.state = QueryState.Complete
    logger.debug('Handler fulfilled request {} from worker {}', id, os.getpid())
    return '', 204
