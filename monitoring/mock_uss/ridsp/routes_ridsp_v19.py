import arrow
import datetime
from typing import List, Optional

import flask
import s2sphere

from uas_standards.astm.f3411.v19.api import (
    ErrorResponse,
    RIDRecentAircraftPosition,
    RIDFlight,
    GetFlightDetailsResponse,
    GetFlightsResponse,
)
from monitoring.monitorlib import geo, rid_v1
from monitoring.monitorlib.rid_automated_testing.injection_api import TestFlight
from implicitdict import StringBasedDateTime
from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from . import behavior
from .database import db


def _get_report(
    flight: TestFlight,
    t_request: datetime.datetime,
    view: s2sphere.LatLngRect,
    include_recent_positions: bool,
) -> Optional[RIDFlight]:
    details = flight.get_details(t_request)
    if not details:
        return None

    recent_states = flight.select_relevant_states(
        view, t_request - rid_v1.NetMaxNearRealTimeDataPeriod, t_request
    )
    if not recent_states:
        # No recent telemetry applicable to view
        return None

    recent_states.sort(key=lambda p: p.timestamp)
    result = RIDFlight(
        id=details.id,
        aircraft_type="NotDeclared",  # TODO: Include aircraft_type in TestFlight API
        current_state=recent_states[-1],
        simulated=True,
    )
    if include_recent_positions:
        recent_positions: List[RIDRecentAircraftPosition] = []
        for recent_state in recent_states:
            recent_positions.append(
                RIDRecentAircraftPosition(
                    time=recent_state.timestamp, position=recent_state.position
                )
            )
        result.recent_positions = recent_positions
    return result


@webapp.route("/mock/ridsp/v1/uss/identification_service_areas/<id>", methods=["POST"])
@requires_scope([rid_v1.SCOPE_WRITE])
def ridsp_notify_isa(id: str):
    return (
        flask.jsonify(
            {"message": "mock_ridsp never solicits subscription notifications"}
        ),
        400,
    )


@webapp.route("/mock/ridsp/v1/uss/flights", methods=["GET"])
@requires_scope([rid_v1.SCOPE_READ])
def ridsp_flights():
    if "view" not in flask.request.args:
        return (
            flask.jsonify(ErrorResponse(message='Missing required "view" parameter')),
            400,
        )
    try:
        view = geo.make_latlng_rect(flask.request.args["view"])
    except ValueError as e:
        return (
            flask.jsonify(ErrorResponse(message="Error parsing view: {}".format(e))),
            400,
        )

    include_recent_positions = (
        flask.request.args.get("include_recent_positions", "False").lower() == "true"
    )

    diagonal = (
        view.lo().get_distance(view.hi()).degrees * geo.EARTH_CIRCUMFERENCE_KM / 360
    )
    if diagonal > rid_v1.NetMaxDisplayAreaDiagonal:
        msg = "Requested diagonal of {} km exceeds limit of {} km".format(
            diagonal, rid_v1.NetMaxDisplayAreaDiagonal
        )
        return flask.jsonify(ErrorResponse(message=msg)), 413

    now = arrow.utcnow().datetime
    flights = []
    tx = db.value
    for test_id, record in tx.tests.items():
        for flight in record.flights:
            reported_flight = _get_report(flight, now, view, include_recent_positions)
            if reported_flight is not None:
                reported_flight = behavior.adjust_reported_flight(
                    flight, reported_flight, tx.behavior
                )
                flights.append(reported_flight)
    return (
        flask.jsonify(
            GetFlightsResponse(timestamp=StringBasedDateTime(now), flights=flights)
        ),
        200,
    )


@webapp.route("/mock/ridsp/v1/uss/flights/<id>/details", methods=["GET"])
@requires_scope([rid_v1.SCOPE_READ])
def ridsp_flight_details(id: str):
    now = arrow.utcnow().datetime
    tx = db.value
    for test_id, record in tx.tests.items():
        for flight in record.flights:
            details = flight.get_details(now)
            if details and details.id == id:
                return flask.jsonify(GetFlightDetailsResponse(details=details)), 200
    return (
        flask.jsonify(ErrorResponse(message="Flight {} not found".format(id))),
        404,
    )
