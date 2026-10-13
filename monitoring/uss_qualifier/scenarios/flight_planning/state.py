import uuid

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    ExecutionStyle,
    FlightID,
    FlightInfo,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    FlightPlanStatus,
    PlanningActivityResponse,
)


class FlightPlanningState:
    """Flights requiring cleanup for one scenario, across its flight planners.

    Each scenario must create its own instance even when sharing planner clients.
    Record IDs before sending requests because a failed request may still create a
    flight. Only a response confirming NotPlanned or Closed removes an ID.
    """

    def __init__(self):
        self._created_flight_ids: dict[FlightPlannerClient, set[FlightID]] = {}

    def get_flight_ids(self, flight_planner: FlightPlannerClient) -> set[FlightID]:
        """Return a copy of this scenario's flights needing cleanup by this planner."""
        return self._created_flight_ids.get(flight_planner, set()).copy()

    def forget_flight(self, flight_planner: FlightPlannerClient, flight_id: FlightID):
        """Stop tracking a flight after closure or a cleanup attempt."""
        if flight_planner in self._created_flight_ids:
            self._created_flight_ids[flight_planner].discard(flight_id)

    def _record_response(
        self, flight_planner: FlightPlannerClient, response: PlanningActivityResponse
    ):
        if response.flight_plan_status in (
            FlightPlanStatus.NotPlanned,
            FlightPlanStatus.Closed,
        ):
            self.forget_flight(flight_planner, response.flight_id)

    def plan_flight(
        self,
        flight_planner: FlightPlannerClient,
        flight_info: FlightInfo,
        execution_style: ExecutionStyle,
        additional_fields: dict | None = None,
    ) -> PlanningActivityResponse:
        flight_id = str(uuid.uuid4())
        self._created_flight_ids.setdefault(flight_planner, set()).add(flight_id)
        response = flight_planner.try_plan_flight(
            flight_info, execution_style, additional_fields, flight_id=flight_id
        )
        self._record_response(flight_planner, response)
        return response

    def update_flight(
        self,
        flight_planner: FlightPlannerClient,
        flight_id: FlightID,
        flight_info: FlightInfo,
        execution_style: ExecutionStyle,
        additional_fields: dict | None = None,
    ) -> PlanningActivityResponse:
        self._created_flight_ids.setdefault(flight_planner, set()).add(flight_id)
        response = flight_planner.try_update_flight(
            flight_id, flight_info, execution_style, additional_fields
        )
        self._record_response(flight_planner, response)
        return response

    def end_flight(
        self,
        flight_planner: FlightPlannerClient,
        flight_id: FlightID,
        execution_style: ExecutionStyle,
    ) -> PlanningActivityResponse:
        response = flight_planner.try_end_flight(flight_id, execution_style)
        self._record_response(flight_planner, response)
        return response
