import arrow
import datetime
from datetime import timedelta
from typing import List, Optional

import flask
import s2sphere
from uas_standards.astm.f3411.v22a.api import (
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
    OperatorLocation,
    LatLngPoint,
    UASID,
    Altitude,
)
from uas_standards.astm.f3411.v22a.constants import (
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
from ...monitorlib.rid_v2 import make_time


def _make_position(p: injection.RIDAircraftPosition) -> RIDAircraftPosition:
    """Convert injection RIDAircraftPosition to F3411-22a"""
    return RIDAircraftPosition(p)


def _make_state(s: injection.RIDAircraftState) -> RIDAircraftState:
    """Convert injection RIDAircraftState to F3411-22a"""
    return RIDAircraftState(
        timestamp=make_time(s.timestamp.datetime),
        timestamp_accuracy=s.timestamp_accuracy,
        operational_status=s.operational_status,
        position=_make_position(s.position),
        track=s.track,
        speed=s.speed,
        speed_accuracy=s.speed_accuracy,
        vertical_speed=s.vertical_speed,
    )


def _make_operator_location(
    position: injection.LatLngPoint, altitude: Optional[injection.OperatorAltitude]
) -> OperatorLocation:
    """Convert injection information to F3411-22a OperatorLocation"""
    operator_location = OperatorLocation(
        position=LatLngPoint(position),
    )
    if altitude:
        operator_location["altitude"] = Altitude(value=altitude.altitude)
        operator_location["altitude_type"] = altitude.altitude_type
    return operator_location


def _make_details(p: injection.RIDFlightDetails) -> RIDFlightDetails:
    """Convert injection RIDFlightDetails to F3411-22a"""
    serial_number = p.serial_number if "serial_number" in p and p.serial_number else ""
    registration_number = (
        p.registration_number
        if "registration_number" in p and p.registration_number
        else ""
    )
    uas_id = (
        p.uas_id
        if "uas_id" in p and p.uas_id
        else UASID(
            serial_number=serial_number,
            registration_number=registration_number,
            utm_id=p.id,
        )
    )
    kwargs = {"id": p.id, "uas_id": uas_id}
    for field in (
        "operator_id",
        "operation_description",
        "auth_data",
        "eu_classification",
    ):
        if field in p:
            kwargs[field] = p[field]
    if "operator_location" in p and p.operator_location:
        kwargs["operator_location"] = _make_operator_location(
            p.operator_location, p.get("operator_altitude")
        )
    return RIDFlightDetails(**kwargs)


def _get_report(
    flight: TestFlight,
    t_request: datetime.datetime,
    view: s2sphere.LatLngRect,
    recent_positions_duration: float,
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
    if recent_positions_duration > 0:
        recent_positions: List[RIDRecentAircraftPosition] = []
        now = arrow.utcnow().datetime
        for recent_state in recent_states:
            if (
                now - recent_state.timestamp.datetime
            ).total_seconds() <= recent_positions_duration:
                recent_positions.append(
                    RIDRecentAircraftPosition(
                        time=make_time(recent_state.timestamp.datetime),
                        position=_make_position(recent_state.position),
                    )
                )
        result.recent_positions = recent_positions
    return result


def rid_v22a_operation(op_id: OperationID):
    op = OPERATIONS[op_id]
    path = op.path.replace("{", "<").replace("}", ">")
    return webapp.route("/mock/ridsp/v2" + path, methods=[op.verb])


@rid_v22a_operation(OperationID.PostIdentificationServiceArea)
@requires_scope(Scope.ServiceProvider)
def ridsp_notify_isa_v22a(id: str):
    return (
        flask.jsonify(
            {"message": "mock_ridsp never solicits subscription notifications"}
        ),
        400,
    )


@rid_v22a_operation(OperationID.SearchFlights)
@requires_scope(Scope.DisplayProvider)
def ridsp_flights_v22a():
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

    try:
        recent_positions_duration = float(
            flask.request.args.get("recent_positions_duration", "0")
        )
    except ValueError as e:
        return (
            flask.jsonify(
                ErrorResponse(
                    message=f"Error parsing recent_positions_duration: {str(e)}"
                )
            ),
            400,
        )
    if recent_positions_duration < 0 or recent_positions_duration > 60:
        return (
            flask.jsonify(
                ErrorResponse(
                    message=f"Invalid recent_positions_duration; must be between 0 and 60, but received {recent_positions_duration}"
                )
            ),
            400,
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
            reported_flight = _get_report(flight, now, view, recent_positions_duration)
            if reported_flight is not None:
                # TODO: Implement Service Provider behaviors for F3411-22a
                # reported_flight = behavior.adjust_reported_flight(
                #     flight, reported_flight, tx.behavior
                # )
                flights.append(reported_flight)
    return (
        flask.jsonify(GetFlightsResponse(timestamp=make_time(now), flights=flights)),
        200,
    )


@rid_v22a_operation(OperationID.GetFlightDetails)
@requires_scope(Scope.DisplayProvider)
def ridsp_flight_details_v22a(id: str):
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
