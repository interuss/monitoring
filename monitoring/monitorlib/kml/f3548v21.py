from typing import List

from pykml.factory import KML_ElementMaker as kml
from uas_standards.astm.f3548.v21.api import (
    OperationalIntent,
    QueryOperationalIntentReferenceParameters,
    QueryOperationalIntentReferenceResponse,
)

from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.kml.generation import (
    GREEN,
    RED,
    TRANSLUCENT_GREEN,
    TRANSLUCENT_LIGHTGRAY,
    TRANSLUCENT_LIGHTGREEN,
    TRANSLUCENT_RED,
    TRANSLUCENT_YELLOW,
    TRANSPARENT,
    YELLOW,
    make_placemark_from_volume,
)
from monitoring.monitorlib.scd import priority_of


def full_op_intent(op_intent: OperationalIntent) -> kml.Folder:
    """Render operational intent information into Placemarks in a KML folder."""
    ref = op_intent.reference
    details = op_intent.details
    name = f"{ref.manager}'s P{priority_of(details)} {ref.state.value} {ref.id}[{ref.version}] @ {ref.ovn}"
    folder = kml.Folder(kml.name(name))
    if "volumes" in details:
        for i, v4_f3548 in enumerate(details.volumes):
            v4 = Volume4D.from_f3548v21(v4_f3548)
            folder.append(
                make_placemark_from_volume(
                    v4,
                    name=f"Nominal volume {i}",
                    style_url=f"#F3548v21{ref.state.value}",
                )
            )
    if "off_nominal_volumes" in details:
        for i, v4_f3548 in enumerate(details.off_nominal_volumes):
            v4 = Volume4D.from_f3548v21(v4_f3548)
            folder.append(
                make_placemark_from_volume(
                    v4,
                    name=f"Off-nominal volume {i}",
                    style_url=f"#F3548v21{ref.state.value}",
                )
            )
    return folder


def op_intent_refs_query(
    req: QueryOperationalIntentReferenceParameters,
    resp: QueryOperationalIntentReferenceResponse,
) -> kml.Placemark:
    """Render the area of interest and response from an operational intent references query into a KML Placemark."""
    v4 = Volume4D.from_f3548v21(req.area_of_interest)
    items = "".join(
        f"<li>{oi.manager}'s {oi.state.value} {oi.id}[{oi.version}]</li>"
        for oi in resp.operational_intent_references
    )
    description = (
        f"<ul>{items}</ul>" if items else "(no operational intent references found)"
    )
    return make_placemark_from_volume(
        v4, name="area_of_interest", style_url="#QueryArea", description=description
    )


def f3548v21_styles() -> List[kml.Style]:
    """Provides KML styles according to F3548-21 operational intent states."""
    return [
        kml.Style(
            kml.LineStyle(kml.color(GREEN), kml.width(3)),
            kml.PolyStyle(kml.color(TRANSLUCENT_LIGHTGRAY)),
            id="F3548v21Accepted",
        ),
        kml.Style(
            kml.LineStyle(kml.color(GREEN), kml.width(3)),
            kml.PolyStyle(kml.color(TRANSLUCENT_GREEN)),
            id="F3548v21Activated",
        ),
        kml.Style(
            kml.LineStyle(kml.color(YELLOW), kml.width(5)),
            kml.PolyStyle(kml.color(TRANSLUCENT_YELLOW)),
            id="F3548v21Nonconforming",
        ),
        kml.Style(
            kml.LineStyle(kml.color(RED), kml.width(5)),
            kml.PolyStyle(kml.color(TRANSLUCENT_RED)),
            id="F3548v21Contingent",
        ),
        kml.Style(
            kml.LineStyle(kml.color(TRANSLUCENT_LIGHTGRAY), kml.width(1)),
            kml.PolyStyle(kml.color(TRANSPARENT)),
            id="F3548v21AcceptedFuture",
        ),
        kml.Style(
            kml.LineStyle(kml.color(TRANSLUCENT_LIGHTGREEN), kml.width(1)),
            kml.PolyStyle(kml.color(TRANSPARENT)),
            id="F3548v21ActivatedFuture",
        ),
        kml.Style(
            kml.LineStyle(kml.color(TRANSLUCENT_YELLOW), kml.width(1)),
            kml.PolyStyle(kml.color(TRANSPARENT)),
            id="F3548v21NonconformingFuture",
        ),
        kml.Style(
            kml.LineStyle(kml.color(TRANSLUCENT_RED), kml.width(1)),
            kml.PolyStyle(kml.color(TRANSPARENT)),
            id="F3548v21ContingentFuture",
        ),
    ]
