import arrow
import datetime
from datetime import timedelta
from typing import List, Optional

import flask
from implicitdict import StringBasedDateTime
import s2sphere
from uas_standards.astm.f3411.v19.api import (
    ErrorResponse,
    RIDRecentAircraftPosition,
    RIDFlight,
    GetFlightDetailsResponse,
    GetFlightsResponse,
    OperationID,
    OPERATIONS,
    RIDAircraftPosition,
    RIDAircraftState,
    RIDFlightDetails,
)
from uas_standards.astm.f3411.v19.constants import (
    Scope,
    NetMaxNearRealTimeDataPeriodSeconds,
    NetMaxDisplayAreaDiagonalKm,
)
from uas_standards.interuss.automated_testing.rid.v1 import injection

from monitoring.monitorlib import geo
from monitoring.monitorlib.rid_automated_testing.injection_api import TestFlight
from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from . import behavior
from .database import db


def _make_state(p: injection.RIDAircraftState) -> RIDAircraftState:
    """Convert injection RIDAircraftState to F3411-19"""
    return RIDAircraftState(p)


def _make_position(p: injection.RIDAircraftPosition) -> RIDAircraftPosition:
    """Convert injection RIDAircraftPosition to F3411-19"""
    return RIDAircraftPosition(p)


def _make_details(p: injection.RIDFlightDetails) -> RIDFlightDetails:
    """Convert injection RIDFlightDetails to F3411-19"""
    return RIDFlightDetails(p)


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
        view,
        t_request - timedelta(seconds=NetMaxNearRealTimeDataPeriodSeconds),
        t_request,
    )
    if not recent_states:
        # No recent telemetry applicable to view
        return None

    recent_states.sort(key=lambda p: p.timestamp)
    result = RIDFlight(
        id=details.id,
        aircraft_type="NotDeclared",  # TODO: Include aircraft_type in TestFlight API
        current_state=_make_state(recent_states[-1]),
        simulated=True,
    )
    if include_recent_positions:
        recent_positions: List[RIDRecentAircraftPosition] = []
        for recent_state in recent_states:
            recent_positions.append(
                RIDRecentAircraftPosition(
                    time=recent_state.timestamp,
                    position=_make_position(recent_state.position),
                )
            )
        result.recent_positions = recent_positions
    return result


def rid_v19_operation(op_id: OperationID):
    op = OPERATIONS[op_id]
    path = op.path.replace("{", "<").replace("}", ">")
    return webapp.route("/mock/ridsp" + path, methods=[op.verb])


@rid_v19_operation(OperationID.PostIdentificationServiceArea)
@requires_scope(Scope.Write)
def ridsp_notify_isa_v19(id: str):
    return (
        flask.jsonify(
            {"message": "mock_ridsp never solicits subscription notifications"}
        ),
        400,
    )


@rid_v19_operation(OperationID.SearchFlights)
@requires_scope(Scope.Read)
def ridsp_flights_v19():
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

    diagonal = geo.get_latlngrect_diagonal_km(view)
    if diagonal > NetMaxDisplayAreaDiagonalKm:
        msg = "Requested diagonal of {} km exceeds limit of {} km".format(
            diagonal, NetMaxDisplayAreaDiagonalKm
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


@rid_v19_operation(OperationID.GetFlightDetails)
@requires_scope(Scope.Read)
def ridsp_flight_details_v19(id: str):
    now = arrow.utcnow().datetime
    tx = db.value
    for test_id, record in tx.tests.items():
        for flight in record.flights:
            details = flight.get_details(now)
            if details and details.id == id:
                return (
                    flask.jsonify(
                        GetFlightDetailsResponse(details=_make_details(details))
                    ),
                    200,
                )
    return (
        flask.jsonify(ErrorResponse(message="Flight {} not found".format(id))),
        404,
    )
