import uuid
from datetime import timedelta

import arrow
import flask
import s2sphere
from loguru import logger
from uas_standards.astm.f3411.v19.api import ErrorResponse
from uas_standards.astm.f3411.v19.constants import Scope
from uas_standards.astm.f3411.v22a.constants import (
    MinHeightResolution,
    MinSpeedResolution,
    MinTrackDirectionResolution,
)
from uas_standards.interuss.automated_testing.rid.v1 import (
    observation as observation_api,
)
from uas_standards.interuss.automated_testing.rid.v1.observation import (
    AltitudeReference,
    MSLAltitude,
    UAType,
)

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.config import KEY_BASE_URL
from monitoring.mock_uss.riddp.database import ObservationSubscription
from monitoring.monitorlib import geo
from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.fetch.rid import Flight
from monitoring.monitorlib.formatting import limit_resolution
from monitoring.monitorlib.geo import egm96_geoid_offset
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.rid import RIDVersion

from . import clustering, database, utm_client
from .behavior import DisplayProviderBehavior
from .config import KEY_RID_VERSION
from .database import db


def _make_flight_observation(
    flight: Flight, view: s2sphere.LatLngRect
) -> observation_api.Flight:
    paths: list[list[observation_api.Position]] = []
    current_path: list[observation_api.Position] = []
    previous_position: observation_api.Position | None = None

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
    msl_alt_m = p.alt - egm96_geoid_offset(s2sphere.LatLng.from_degrees(p.lat, p.lng))
    msl_alt = MSLAltitude(meters=msl_alt_m, reference_datum=AltitudeReference.EGM96)
    current_state = observation_api.CurrentState(
        timestamp=p.time.isoformat(),
        timestamp_accuracy=flight.timestamp_accuracy,
        operational_status=flight.operational_status,
        track=limit_resolution(flight.track, MinTrackDirectionResolution),
        speed=limit_resolution(flight.speed, MinSpeedResolution),
        speed_accuracy=flight.speed_accuracy,
        vertical_speed=flight.vertical_speed,
    )
    h = p.get("height")
    if h:
        h.distance = limit_resolution(h.distance, MinHeightResolution)
    return observation_api.Flight(
        id=flight.id,
        aircraft_type=(
            flight.aircraft_type if flight.aircraft_type else UAType.NotDeclared
        ),
        most_recent_position=observation_api.Position(
            lat=p.lat,
            lng=p.lng,
            alt=p.alt,
            height=h,
            msl_alt=msl_alt,
            accuracy_v=p.accuracy_v,
            accuracy_h=p.accuracy_h,
        ),
        recent_paths=[observation_api.Path(positions=path) for path in paths],
        current_state=current_state,
    )


@webapp.route("/riddp/observation/display_data", methods=["GET"])
@requires_scope(Scope.Read)
def riddp_display_data() -> tuple[flask.Response, int]:
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
            flask.jsonify(ErrorResponse(message=f"Error parsing view: {e}")),
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

    with db.transact() as tx:
        # Find an existing subscription to serve this request
        subscription: ObservationSubscription | None = None
        t_max = (
            arrow.utcnow() + timedelta(seconds=1)
        ).datetime  # Don't rely on subscriptions very near their expiration
        tx.value.subscriptions = [
            s
            for s in tx.value.subscriptions
            if s.upsert_result.subscription
            and s.upsert_result.subscription.time_end > t_max
        ]
        for existing_subscription in tx.value.subscriptions:
            assert isinstance(existing_subscription, ObservationSubscription)
            sub_rect = existing_subscription.bounds.to_latlngrect()
            if sub_rect.contains(view):
                subscription = existing_subscription
                logger.debug(
                    f"Existing subscription {subscription.upsert_result.subscription.id} indicates ISAs: {','.join(isa.id for isa in subscription.get_isas())}"
                )
                break

        # No existing subscription suffices; create a new one
        if subscription is None:
            buffer_m = 1000  # meters beyond the view box triggering creation of this subscription
            dt = timedelta(seconds=30)  # duration of new subscription
            sub_bounds = geo.LatLngBoundingBox.from_latlng_rect(view).expand(
                buffer_m, buffer_m, buffer_m, buffer_m
            )
            upsert_result = mutate.upsert_subscription(
                area_vertices=sub_bounds.to_vertices(),
                alt_lo=0,
                alt_hi=100000,
                start_time=None,
                end_time=(arrow.utcnow() + dt).datetime,
                uss_base_url=webapp.config[KEY_BASE_URL] + "/mock/riddp",
                subscription_id=str(uuid.uuid4()),
                rid_version=rid_version,
                utm_client=utm_client,
            )
            if not upsert_result.success:
                msg = f"Error establishing ISA subscription in DSS: {upsert_result.errors}"
                logger.error(msg)
                response = ErrorResponse(message=msg)
                response["upsert_subscription"] = upsert_result
                return flask.jsonify(response), 412
            logger.debug(
                f"New subscription indicated ISAs: {','.join(isa.id for isa in upsert_result.isas)}"
            )
            subscription = ObservationSubscription(
                bounds=sub_bounds, upsert_result=upsert_result, updates=[]
            )
            tx.value.subscriptions.append(subscription)

    # Fetch flights from each unique flights URL
    validated_flights: list[Flight] = []
    tx = db.value
    flight_info: dict[str, database.FlightInfo] = {k: v for k, v in tx.flights.items()}
    behavior: DisplayProviderBehavior = tx.behavior

    for flights_url, uss in subscription.flights_urls.items():
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
    with db.transact() as tx:
        for k, v in flight_info.items():
            tx.value.flights[k] = v

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
        clusters = clustering.make_clusters(flights, view.lo(), view.hi(), rid_version)
        response = observation_api.GetDisplayDataResponse(clusters=clusters)
    return flask.jsonify(response), 200


@webapp.route("/riddp/observation/display_data/<flight_id>", methods=["GET"])
@requires_scope(Scope.Read)
def riddp_flight_details(flight_id: str) -> tuple[str, int] | flask.Response:
    """Implements get flight details endpoint per automated testing API."""
    tx = db.value
    flight_info = tx.flights.get(flight_id)
    if not flight_info:
        return f'Flight "{flight_id}" not found', 404

    rid_version: RIDVersion = webapp.config[KEY_RID_VERSION]
    flight_details = fetch.flight_details(
        flight_info.flights_url, flight_id, True, rid_version, utm_client
    )
    details = flight_details.details

    result = observation_api.GetDetailsResponse(
        operator=observation_api.Operator(
            id=details.operator_id,
            location=None,
            altitude=observation_api.OperatorAltitude(),
        ),
        uas=observation_api.UAS(
            id=details.arbitrary_uas_id,
            eu_classification=details.eu_classification,
        ),
    )
    if details.operator_location is not None:
        result.operator.location = observation_api.LatLngPoint(
            lat=details.operator_location.lat,
            lng=details.operator_location.lng,
        )
    if details.operator_altitude is not None:
        result.operator.altitude.altitude = details.operator_altitude.value
    if details.operator_altitude_type is not None:
        result.operator.altitude.altitude_type = (
            observation_api.OperatorAltitudeAltitudeType(details.operator_altitude_type)
        )
    return flask.jsonify(result)
