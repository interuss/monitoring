from dataclasses import dataclass
from typing import Dict, List, Type, Optional, get_type_hints, Protocol

from implicitdict import ImplicitDict
from loguru import logger
from lxml import etree
from pykml.factory import KML_ElementMaker as kml
from pykml.util import format_xml_with_cdata

from monitoring.monitorlib.scd import priority_of
from monitoring.uss_qualifier.reports.sequence_view.summary_types import TestedScenario
from uas_standards.astm.f3548.v21.api import (
    QueryOperationalIntentReferenceParameters,
    QueryOperationalIntentReferenceResponse,
    GetOperationalIntentDetailsResponse,
)

from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.fetch import QueryType, Query
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.kml import (
    make_placemark_from_volume,
    query_styles,
    f3548v21_styles,
    flight_planning_styles,
)
from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    UpsertFlightPlanRequest,
    UpsertFlightPlanResponse,
)


class QueryKMLRenderer(Protocol):
    def __call__(
        self, query: Query, req: ImplicitDict, resp: ImplicitDict
    ) -> List[kml.Element]:
        """Function that renders the provided query information into KML elements.

        Args:
            query: Raw query to render to KML.
            req: Query request, parsed into the annotated type.
            resp: Query response, parsed into the annotated type.

        Returns: List of KML elements to include the folder for the query.
        """


@dataclass
class QueryKMLRenderInfo(object):
    renderer: QueryKMLRenderer
    include_query: bool
    request_type: Optional[Type[ImplicitDict]]
    response_type: Optional[Type[ImplicitDict]]


_query_kml_renderers: Dict[QueryType, QueryKMLRenderInfo] = {}


def query_kml_renderer(query_type: QueryType):
    """Decorator to label a function that renders KML for a particular query type.

    Decorated functions should follow the QueryKMLRenderer Protocol, but may omit any of the parameters.

    Args:
        query_type: The type of query the decorated function can render KML for.
    """

    def register_renderer(func: QueryKMLRenderer) -> QueryKMLRenderer:
        hints = get_type_hints(func)
        _query_kml_renderers[query_type] = QueryKMLRenderInfo(
            renderer=func,
            include_query="query" in hints,
            request_type=hints.get("req", None),
            response_type=hints.get("resp", None),
        )
        return func

    return register_renderer


def make_scenario_kml(scenario: TestedScenario) -> str:
    """Make KML file visualizing the provided scenario.

    Args:
        scenario: Summarized scenario to visualize with KML.

    Returns: KML text that can be written to file.
    """
    top_folder = kml.Folder(kml.name(scenario.name))
    for epoch in scenario.epochs:
        if not epoch.case:
            continue  # Only support test cases for now
        case_folder = kml.Folder(kml.name(epoch.case.name))
        top_folder.append(case_folder)
        for step in epoch.case.steps:
            step_folder = kml.Folder(kml.name(step.name))
            case_folder.append(step_folder)
            for event in step.events:
                if not event.query or "query_type" not in event.query:
                    continue  # Only visualize queries of known types
                if event.query.query_type not in _query_kml_renderers:
                    continue  # Only visualize queries with renderers
                render_info = _query_kml_renderers[event.query.query_type]
                participant = (
                    f"{event.query.participant_id} "
                    if "participant_id" in event.query
                    else ""
                )
                query_folder = kml.Folder(
                    kml.name(
                        f"E{event.event_index}: {participant}{event.query.query_type.value}"
                    )
                )
                step_folder.append(query_folder)

                kwargs = {}
                if render_info.include_query:
                    kwargs["query"] = event.query
                if render_info.request_type:
                    try:
                        kwargs["req"] = ImplicitDict.parse(
                            event.query.request.json,
                            render_info.request_type,
                        )
                    except ValueError as e:
                        msg = f"Error parsing request into {render_info.request_type.__name__}"
                        logger.warning(msg)
                        query_folder.append(
                            kml.Folder(
                                kml.name(msg),
                                kml.description(stacktrace_string(e)),
                            )
                        )
                        continue
                if (
                    render_info.response_type is not type(None)
                    and render_info.response_type
                ):
                    try:
                        kwargs["resp"] = ImplicitDict.parse(
                            event.query.response.json,
                            render_info.response_type,
                        )
                    except ValueError as e:
                        msg = f"Error parsing response into {render_info.response_type.__name__}"
                        logger.warning(msg)
                        query_folder.append(
                            kml.Folder(
                                kml.name(msg),
                                kml.description(stacktrace_string(e)),
                            )
                        )
                        continue
                try:
                    query_folder.extend(render_info.renderer(**kwargs))
                except TypeError as e:
                    msg = f"Error rendering {render_info.renderer.__name__}"
                    logger.warning(msg)
                    query_folder.append(
                        kml.Folder(
                            kml.name(msg),
                            kml.description(stacktrace_string(e)),
                        )
                    )
    doc = kml.kml(
        kml.Document(
            *query_styles(), *f3548v21_styles(), *flight_planning_styles(), top_folder
        )
    )
    return etree.tostring(format_xml_with_cdata(doc), pretty_print=True).decode("utf-8")


@query_kml_renderer(QueryType.F3548v21DSSQueryOperationalIntentReferences)
def render_query_op_intent_references(
    req: QueryOperationalIntentReferenceParameters,
    resp: QueryOperationalIntentReferenceResponse,
):
    if "area_of_interest" not in req or not req.area_of_interest:
        return [
            kml.Folder(kml.name("Error: area_of_interest not specified in request"))
        ]
    v4 = Volume4D.from_f3548v21(req.area_of_interest)
    items = "".join(
        f"<li>{oi.manager}'s {oi.state.value} {oi.id}[{oi.version}]</li>"
        for oi in resp.operational_intent_references
    )
    description = (
        f"<ul>{items}</ul>" if items else "(no operational intent references found)"
    )
    return [
        make_placemark_from_volume(
            v4, name="area_of_interest", style_url="#QueryArea", description=description
        )
    ]


@query_kml_renderer(QueryType.F3548v21USSGetOperationalIntentDetails)
def render_get_op_intent_details(resp: GetOperationalIntentDetailsResponse):
    ref = resp.operational_intent.reference
    name = f"{ref.manager}'s P{priority_of(resp.operational_intent.details)} {ref.state.value} {ref.id}[{ref.version}] @ {ref.ovn}"
    folder = kml.Folder(kml.name(name))
    if "volumes" in resp.operational_intent.details:
        for i, v4_f3548 in enumerate(resp.operational_intent.details.volumes):
            v4 = Volume4D.from_f3548v21(v4_f3548)
            folder.append(
                make_placemark_from_volume(
                    v4,
                    name=f"Nominal volume {i}",
                    style_url=f"#F3548v21{resp.operational_intent.reference.state.value}",
                )
            )
    if "off_nominal_volumes" in resp.operational_intent.details:
        for i, v4_f3548 in enumerate(
            resp.operational_intent.details.off_nominal_volumes
        ):
            v4 = Volume4D.from_f3548v21(v4_f3548)
            folder.append(
                make_placemark_from_volume(
                    v4,
                    name=f"Off-nominal volume {i}",
                    style_url=f"#F3548v21{resp.operational_intent.reference.state.value}",
                )
            )
    return [folder]


@query_kml_renderer(QueryType.InterUSSFlightPlanningV1UpsertFlightPlan)
def render_flight_planning_upsert_flight_plan(
    req: UpsertFlightPlanRequest, resp: UpsertFlightPlanResponse
):
    folder = kml.Folder(
        kml.name(
            f"Activity {resp.planning_result.value}, flight {resp.flight_plan_status.value}"
        )
    )
    basic_info = req.flight_plan.basic_information
    for i, v4_flight_planning in enumerate(basic_info.area):
        v4 = Volume4D.from_flight_planning_api(v4_flight_planning)
        folder.append(
            make_placemark_from_volume(
                v4,
                name=f"Volume {i}",
                style_url=f"#{basic_info.usage_state.value}_{basic_info.uas_state.value}",
            )
        )
    return [folder]
