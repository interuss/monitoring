from dataclasses import dataclass
from typing import Protocol, get_type_hints

from implicitdict import ImplicitDict
from loguru import logger
from lxml import etree
from pykml.factory import KML_ElementMaker as kml
from pykml.util import format_xml_with_cdata
from uas_standards.astm.f3548.v21.api import (
    GetOperationalIntentDetailsResponse,
    QueryOperationalIntentReferenceParameters,
    QueryOperationalIntentReferenceResponse,
)
from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    UpsertFlightPlanRequest,
    UpsertFlightPlanResponse,
)

from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.fetch import Query, QueryType
from monitoring.monitorlib.kml.f3548v21 import (
    f3548v21_styles,
    full_op_intent,
    op_intent_refs_query,
)
from monitoring.monitorlib.kml.flight_planning import (
    flight_planning_styles,
    upsert_flight_plan,
)
from monitoring.monitorlib.kml.generation import query_styles
from monitoring.uss_qualifier.reports.sequence_view.summary_types import TestedScenario


class QueryKMLRenderer(Protocol):
    def __call__(
        self, query: Query, req: ImplicitDict, resp: ImplicitDict
    ) -> list[kml.Element]:
        """Function that renders the provided query information into KML elements.

        Args:
            query: Raw query to render to KML.
            req: Query request, parsed into the annotated type.
            resp: Query response, parsed into the annotated type.

        Returns: List of KML elements to include the folder for the query.
        """


@dataclass
class QueryKMLRenderInfo:
    renderer: QueryKMLRenderer
    include_query: bool
    request_type: type[ImplicitDict] | None
    response_type: type[ImplicitDict] | None


_query_kml_renderers: dict[QueryType, QueryKMLRenderInfo] = {}


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
                except (TypeError, KeyError, ValueError) as e:
                    msg = f"Error rendering {render_info.renderer.__name__}"
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
    return [op_intent_refs_query(req, resp)]


@query_kml_renderer(QueryType.F3548v21USSGetOperationalIntentDetails)
def render_get_op_intent_details(resp: GetOperationalIntentDetailsResponse):
    return [full_op_intent(resp.operational_intent)]


@query_kml_renderer(QueryType.InterUSSFlightPlanningV1UpsertFlightPlan)
def render_flight_planning_upsert_flight_plan(
    req: UpsertFlightPlanRequest, resp: UpsertFlightPlanResponse
):
    return [upsert_flight_plan(req, resp)]
