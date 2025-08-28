from pykml.factory import KML_ElementMaker as kml
from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    UpsertFlightPlanRequest,
    UpsertFlightPlanResponse,
)

from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.kml.generation import (
    GREEN,
    RED,
    TRANSLUCENT_GRAY,
    TRANSLUCENT_GREEN,
    YELLOW,
    make_placemark_from_volume,
)


def upsert_flight_plan(req: UpsertFlightPlanRequest, resp: UpsertFlightPlanResponse):
    """Render a flight planning action into a KML folder."""
    basic_info = req.flight_plan.basic_information
    folder = kml.Folder(
        kml.name(
            f"Activity {resp.planning_result.value}, flight {resp.flight_plan_status.value}"
        )
    )
    for i, v4_flight_planning in enumerate(basic_info.area or []):
        v4 = Volume4D.from_flight_planning_api(v4_flight_planning)
        folder.append(
            make_placemark_from_volume(
                v4,
                name=f"Volume {i}",
                style_url=f"#{basic_info.usage_state.value}_{basic_info.uas_state.value}",
            )
        )
    return folder


def flight_planning_styles() -> list:
    """Provides KML styles with names in the form {FlightPlanState}_{AirspaceUsageState}."""
    return [
        kml.Style(
            kml.LineStyle(kml.color(GREEN), kml.width(3)),
            kml.PolyStyle(kml.color(TRANSLUCENT_GRAY)),
            id="Planned_Nominal",
        ),
        kml.Style(
            kml.LineStyle(kml.color(GREEN), kml.width(3)),
            kml.PolyStyle(kml.color(TRANSLUCENT_GREEN)),
            id="InUse_Nominal",
        ),
        kml.Style(
            kml.LineStyle(kml.color(YELLOW), kml.width(5)),
            kml.PolyStyle(kml.color(TRANSLUCENT_GREEN)),
            id="InUse_OffNominal",
        ),
        kml.Style(
            kml.LineStyle(kml.color(RED), kml.width(5)),
            kml.PolyStyle(kml.color(TRANSLUCENT_GREEN)),
            id="InUse_Contingent",
        ),
    ]
