from typing import List, Iterable, Dict, Optional

from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.scd.v1.constants import Scope as ScopeSCD
from uas_standards.interuss.automated_testing.flight_planning.v1.constants import (
    Scope as ScopeFlightPlanning,
)

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.uss_qualifier.reports.report import ParticipantID
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlannerConfiguration,
)


class FlightPlannerSpecification(ImplicitDict):
    flight_planner: FlightPlannerConfiguration


class FlightPlannerResource(Resource[FlightPlannerSpecification]):
    client: FlightPlannerClient
    participant_id: ParticipantID

    def __init__(
        self,
        specification: FlightPlannerSpecification,
        resource_origin: str,
        auth_adapter: AuthAdapterResource,
    ):
        super(FlightPlannerResource, self).__init__(specification, resource_origin)
        if (
            "scd_injection_base_url" in specification.flight_planner
            and specification.flight_planner.scd_injection_base_url
        ):
            auth_adapter.assert_scopes_available(
                scopes_required={
                    ScopeSCD.Inject: "inject user flight planning commands to USSs under test",
                },
                consumer_name=f"{self.__class__.__name__} using legacy scd injection API",
            )
        elif (
            "v1_base_url" in specification.flight_planner
            and specification.flight_planner.v1_base_url
        ):
            auth_adapter.assert_scopes_available(
                scopes_required={
                    ScopeFlightPlanning.DirectAutomatedTest: "act as test director to instruct USSs under test to perform various test preparation activities related to flight planning testing",
                    ScopeFlightPlanning.Plan: "act as user performing flight planning operations on USSs under test",
                },
                consumer_name=f"{self.__class__.__name__} using flight_planner v1 API",
            )
        else:
            raise NotImplementedError(
                "The means by which to interact with the flight planner is not currently supported in FlightPlannerResource (neither scd_injection_base_url nor v1_base_url were specified)"
            )

        self.client = specification.flight_planner.to_client(auth_adapter.adapter)
        self.participant_id = specification.flight_planner.participant_id


class FlightPlannersSpecification(ImplicitDict):
    flight_planners: List[FlightPlannerConfiguration]


class FlightPlannersResource(Resource[FlightPlannersSpecification]):
    flight_planners: List[FlightPlannerResource]

    def __init__(
        self,
        specification: FlightPlannersSpecification,
        resource_origin: str,
        auth_adapter: AuthAdapterResource,
    ):
        super(FlightPlannersResource, self).__init__(specification, resource_origin)
        self._specification = specification
        self._auth_adapter = auth_adapter
        self.flight_planners = [
            FlightPlannerResource(
                FlightPlannerSpecification(flight_planner=p),
                f"instance {i + 1} in {resource_origin}",
                auth_adapter,
            )
            for i, p in enumerate(specification.flight_planners)
        ]

    def make_subset(self, select_indices: Iterable[int]) -> List[FlightPlannerResource]:
        return [self.flight_planners[i] for i in select_indices]


class FlightPlannerCombinationSelectorSpecification(ImplicitDict):
    must_include: Optional[List[ParticipantID]]
    """The set of flight planners which must be included in every combination"""

    maximum_roles: Optional[Dict[ParticipantID, int]]
    """Maximum number of roles a particular participant may fill in any given combination"""


class FlightPlannerCombinationSelectorResource(
    Resource[FlightPlannerCombinationSelectorSpecification]
):
    _specification: FlightPlannerCombinationSelectorSpecification

    def __init__(
        self,
        specification: FlightPlannerCombinationSelectorSpecification,
        resource_origin: str,
    ):
        super(FlightPlannerCombinationSelectorResource, self).__init__(
            specification, resource_origin
        )
        self._specification = specification

    def is_valid_combination(
        self, flight_planners: Dict[ResourceID, FlightPlannerResource]
    ):
        participants = [p.participant_id for p in flight_planners.values()]

        # Apply must_include criteria
        if "must_include" in self._specification:
            for required_participant in self._specification.must_include:
                if required_participant not in participants:
                    return False

        # Apply maximum_roles criteria
        if "maximum_roles" in self._specification:
            for (
                limited_participant,
                max_count,
            ) in self._specification.maximum_roles.items():
                count = sum(
                    (1 if participant == limited_participant else 0)
                    for participant in participants
                )
                if count > max_count:
                    return False

        return True
