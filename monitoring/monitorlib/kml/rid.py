from datetime import timedelta

from pykml.factory import KML_ElementMaker as kml
from uas_standards.astm.f3411.v22a.api import GetFlightsResponse
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    ChangeTestResponse,
    CreateTestParameters,
)

from monitoring.monitorlib.kml.generation import (
    add_linestring,
    add_point,
    make_basic_placemark,
)


def create_test(req: CreateTestParameters, resp: ChangeTestResponse) -> list:
    result = []
    for test_flight in resp.injected_flights:
        folder = kml.Folder(kml.name(f"Test flight {test_flight.injection_id}"))
        requested_flight = None
        for flight in req.requested_flights:
            if flight.injection_id == test_flight.injection_id:
                requested_flight = flight
        for i, telemetry in enumerate(test_flight.telemetry):
            if (
                "position" in telemetry
                and telemetry.position
                and "lat" in telemetry.position
                and telemetry.position.lat
                and "lng" in telemetry.position
                and telemetry.position.lng
            ):
                style_url = "#modifiedtelemetry"
                if requested_flight and len(requested_flight.telemetry) > i:
                    rt = requested_flight.telemetry[i]
                    if (
                        "position" in rt
                        and rt.position
                        and rt.position.lat == telemetry.position.lat
                        and rt.position.lng == telemetry.position.lng
                    ):
                        style_url = "#unmodifiedtelemetry"
                if "timestamp" in telemetry and telemetry.timestamp:
                    time_start = telemetry.timestamp.datetime
                    if i < len(test_flight.telemetry) - 1:
                        tt = test_flight.telemetry[i + 1]
                        if "timestamp" in tt and tt.timestamp:
                            time_end = tt.timestamp.datetime
                        else:
                            time_end = time_start + timedelta(seconds=1)
                    else:
                        time_end = time_start + timedelta(seconds=1)
                else:
                    time_start = None
                    time_end = None
                point = make_basic_placemark(
                    name=f"Telemetry {i}",
                    style_url=style_url,
                    time_start=time_start,
                    time_end=time_end,
                )
                add_point(point, telemetry.position.lat, telemetry.position.lng)
                folder.append(point)
        result.append(folder)
    return result


def get_flights_v22a(url: str, resp: GetFlightsResponse) -> list:
    result = []
    # TODO: render request bounding box from query parameter in url
    for flight in resp.flights or [] if "flights" in resp else []:
        folder = kml.Folder(kml.name(flight.id))
        if (
            "current_state" in flight
            and flight.current_state
            and "lat" in flight.current_state.position
            and flight.current_state.position.lat
            and "lng" in flight.current_state.position
            and flight.current_state.position.lng
        ):
            point = make_basic_placemark(
                name=f"{flight.aircraft_type.name} {flight.id}{' SIMULATED' if flight.simulated else ''}",
                style_url="#aircraft",
            )
            add_point(
                point,
                flight.current_state.position.lat,
                flight.current_state.position.lng,
            )
            folder.append(point)
        if "recent_positions" in flight and flight.recent_positions:
            tail = make_basic_placemark(
                name=f"{flight.id} recent positions", style_url="#ridtail"
            )
            add_linestring(
                tail,
                [
                    (rp.position.lng, rp.position.lat, 0)
                    for rp in flight.recent_positions
                    if "lng" in rp.position
                    and rp.position.lng
                    and "lat" in rp.position
                    and rp.position.lat
                ],
            )
            folder.append(tail)

        result.append(folder)
    return result


def rid_styles() -> list:
    """Provides KML styles used by RID visualizations above."""
    return [
        kml.Style(
            kml.IconStyle(
                kml.scale(1.4),
                kml.Icon(
                    kml.href(
                        "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
                    )
                ),
            ),
            id="unmodifiedtelemetry",
        ),
        kml.Style(
            kml.IconStyle(
                kml.scale(1.4),
                kml.Icon(
                    kml.href(
                        "http://maps.google.com/mapfiles/kml/shapes/placemark_square.png"
                    )
                ),
            ),
            id="modifiedtelemetry",
        ),
        kml.Style(
            kml.IconStyle(
                kml.scale(1.4),
                kml.Icon(
                    kml.href("http://maps.google.com/mapfiles/kml/shapes/airports.png")
                ),
            ),
            id="aircraft",
        ),
    ]
