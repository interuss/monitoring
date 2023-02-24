from datetime import timedelta
from typing import Tuple

import flask
from uas_standards.astm.f3411.v19.constants import Scope

from . import handling
from .app import webapp
from .config import KEY_QUERY_TIMEOUT
from .oauth import requires_scope
from .requests import RIDObservationGetDisplayDataRequest, RIDObservationGetDetailsRequest

timeout = timedelta(seconds=webapp.config[KEY_QUERY_TIMEOUT])


@webapp.route('/riddp/observation/display_data', methods=['GET'])
@requires_scope([Scope.Read])
def rid_observation_display_data() -> Tuple[str, int]:
    """Implements retrieval of current display data per automated testing API."""
    return handling.fulfill_query(RIDObservationGetDisplayDataRequest(view=flask.request.args['view']), timeout)


@webapp.route('/riddp/observation/display_data/<flight_id>', methods=['GET'])
@requires_scope([Scope.Read])
def rid_observation_flight_details(flight_id: str) -> Tuple[str, int]:
    """Implements get flight details endpoint per automated testing API."""
    return handling.fulfill_query(RIDObservationGetDetailsRequest(id=flight_id), timeout)
