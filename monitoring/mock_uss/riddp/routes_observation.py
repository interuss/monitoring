from typing import Dict, List, Optional, Tuple

import arrow
import flask
from loguru import logger
import s2sphere
from uas_standards.astm.f3411.v19.api import ErrorResponse
from uas_standards.astm.f3411.v19.constants import Scope

from monitoring.monitorlib import geo
from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.fetch.rid import Flight, FetchedISAs
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.rid_automated_testing import observation_api
from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from . import clustering, database, utm_client
from .behavior import DisplayProviderBehavior
from .config import KEY_RID_VERSION
from .database import db


def _make_flight_observation(
    flight: Flight, view: s2sphere.LatLngRect
) -> observation_api.Flight:
    paths: List[List[observation_api.Position]] = []
    current_path: List[observation_api.Position] = []
    previous_position: Optional[observation_api.Position] = None

    lat_min = view.lat_lo().degrees
    lat_max = view.lat_hi().degrees
    lng_min = view.lng_lo().degrees
    lng_max = view.lng_hi().degrees

    # Decompose recent positions into a list of contiguous paths
    for p in flight.recent_positions:
        position_report = observation_api.Position(lat=p.lat, lng=p.lng, alt=p.alt)

        inside_view = lat_min <= p.lat <= lat_max and lng_min <= p.lng <= lng_max
        if inside_view:
            # This point is inside the view
            if not current_path and previous_position:
                # Positions were previously outside the view but this one is in
                current_path.append(previous_position)
            current_path.append(position_report)
        else:
            # This point is outside the view
            if current_path:
                # Positions were previously inside the view but this one is out
                current_path.append(position_report)
                paths.append(current_path)
                current_path = []
        previous_position = position_report
    if current_path:
        paths.append(current_path)

    p = flight.most_recent_position
    return observation_api.Flight(
        id=flight.id,
        most_recent_position=observation_api.Position(lat=p.lat, lng=p.lng, alt=p.alt),
        recent_paths=[observation_api.Path(positions=path) for path in paths],
    )


@webapp.route("/riddp/observation/display_data", methods=["GET"])
@requires_scope([Scope.Read])
def riddp_display_data() -> Tuple[str, int]:
    """Implements retrieval of current display data per automated testing API."""

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

    rid_version: RIDVersion = webapp.config[KEY_RID_VERSION]

    # Determine what kind of response to produce
    diagonal = geo.get_latlngrect_diagonal_km(view)
    if diagonal > rid_version.max_diagonal_km:
        return (
            flask.jsonify(ErrorResponse(message="Requested diagonal was too large")),
            413,
        )

    # Get ISAs in the DSS
    t = arrow.utcnow().datetime
    isa_list: FetchedISAs = fetch.isas(view, t, t, rid_version, utm_client)
    if not isa_list.success:
        msg = f"Error fetching ISAs from DSS: {isa_list.error}"
        logger.error(msg)
        response = ErrorResponse(message=msg)
        response["fetched_isas"] = isa_list
        return flask.jsonify(response), 412

    # Fetch flights from each unique flights URL
    validated_flights: List[Flight] = []
    tx = db.value
    flight_info: Dict[str, database.FlightInfo] = {k: v for k, v in tx.flights.items()}
    behavior: DisplayProviderBehavior = tx.behavior

    for flights_url, uss in isa_list.flights_urls.items():
        if uss in behavior.do_not_display_flights_from:
            continue
        flights_response = fetch.uss_flights(
            flights_url, view, True, rid_version, utm_client
        )
        if not flights_response.success:
            msg = (
                f"Error querying {flights_url} from {uss}: {flights_response.errors[0]}"
            )
            logger.error(msg)
            response = ErrorResponse(message=msg)
            response["fetched_uss_flights"] = flights_response
            return flask.jsonify(response), 412
        for flight in flights_response.flights:
            flight_errors = flight.errors()
            if flight_errors:
                msg = (
                    f"Errors while validating Flight data structure returned from {flights_url} by {uss}:\n"
                    + "\n".join(flight_errors)
                )
                logger.error(msg)
                response = ErrorResponse(message=msg)
                response["flight_validation_errors"] = flight_errors
                response["fetched_uss_flights"] = flights_response
                return flask.jsonify(response), 412
            validated_flights.append(flight)
            flight_info[flight.id] = database.FlightInfo(flights_url=flights_url)

    # Update links between flight IDs and flight URLs
    with db as tx:
        for k, v in flight_info.items():
            tx.flights[k] = v

    # Make and return response
    flights = [_make_flight_observation(f, view) for f in validated_flights]
    if behavior.always_omit_recent_paths:
        for f in flights:
            f.recent_paths = None
    if diagonal <= rid_version.max_details_diagonal_km:
        # Construct detailed flights response
        response = observation_api.GetDisplayDataResponse(flights=flights)
    else:
        # Construct clusters response
        clusters = clustering.make_clusters(flights, view.lo(), view.hi())
        response = observation_api.GetDisplayDataResponse(clusters=clusters)
    return flask.jsonify(response)


@webapp.route("/riddp/observation/display_data/<flight_id>", methods=["GET"])
@requires_scope([Scope.Read])
def riddp_flight_details(flight_id: str) -> Tuple[str, int]:
    """Implements get flight details endpoint per automated testing API."""

    tx = db.value
    if flight_id not in tx.flights:
        return 'Flight "{}" not found'.format(flight_id), 404

    return flask.jsonify(observation_api.GetDetailsResponse())
