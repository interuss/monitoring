from typing import Tuple

import flask

from monitoring.monitorlib import rid_v2
from . import handling
from .app import webapp
from .oauth import requires_scope
from .requests import RIDObservationGetDisplayDataRequest, RIDObservationGetDetailsRequest


@webapp.route('/riddp/observation/display_data', methods=['GET'])
@requires_scope([rid_v2.SCOPE_DP])
def rid_observation_display_data() -> Tuple[str, int]:
    """Implements retrieval of current display data per automated testing API."""
    return handling.fulfill_query(RIDObservationGetDisplayDataRequest(view=flask.request.args['view']))


@webapp.route('/riddp/observation/display_data/<flight_id>', methods=['GET'])
@requires_scope([rid_v2.SCOPE_DP])
def rid_observation_flight_details(flight_id: str) -> Tuple[str, int]:
    """Implements get flight details endpoint per automated testing API."""
    return handling.fulfill_query(RIDObservationGetDetailsRequest(id=flight_id))
