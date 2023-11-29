from abc import ABC, abstractmethod
from typing import Optional, Set

from monitoring.monitorlib.clients.flight_planning.test_preparation import (
    TestPreparationActivityResponse,
)

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightInfo,
    FlightID,
    ExecutionStyle,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResponse,
)
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.uss_qualifier.configurations.configuration import ParticipantID


class PlanningActivityError(QueryError):
    pass


class FlightPlannerClient(ABC):
    """Client to interact with a USS as a user performing flight planning activities and as the test director preparing for tests involving flight planning activities."""

    participant_id: ParticipantID
    created_flight_ids: Set[FlightID]

    def __init__(self, participant_id: ParticipantID):
        self.participant_id = participant_id
        self.created_flight_ids: Set[FlightID] = set()

    # ===== Emulation of user actions =====

    @abstractmethod
    def try_plan_flight(
        self,
        flight_info: FlightInfo,
        execution_style: ExecutionStyle,
        additional_fields: Optional[dict] = None,
    ) -> PlanningActivityResponse:
        """Instruct the USS to emulate a normal user trying to plan the described flight.

        Raises:
            * PlanningActivityError
        """
        raise NotImplementedError()

    @abstractmethod
    def try_update_flight(
        self,
        flight_id: FlightID,
        updated_flight_info: FlightInfo,
        execution_style: ExecutionStyle,
        additional_fields: Optional[dict] = None,
    ) -> PlanningActivityResponse:
        """Instruct the USS to emulate a normal user trying to update the specified flight as described.

        Raises:
            * PlanningActivityError
        """
        raise NotImplementedError()

    @abstractmethod
    def try_end_flight(
        self, flight_id: FlightID, execution_style: ExecutionStyle
    ) -> PlanningActivityResponse:
        """Instruct the USS to emulate a normal user trying to end the specified flight.

        Raises:
            * PlanningActivityError
        """
        raise NotImplementedError()

    # ===== Test preparation activities =====

    @abstractmethod
    def report_readiness(self) -> TestPreparationActivityResponse:
        """Acting as test director, ask the USS about its readiness to use its flight planning interface for automated testing.

        Raises:
            * PlanningActivityError
        """
        raise NotImplementedError()

    @abstractmethod
    def clear_area(self, area: Volume4D) -> TestPreparationActivityResponse:
        """Acting as test director, instruct the USS to close/end/remove all flights it manages within the specified area.

        Raises:
            * PlanningActivityError
        """
        raise NotImplementedError()

    @abstractmethod
    def get_base_url(self) -> str:
        """
        Get the base_url associated with this FlightPlannerClient
        Returns:

        """
        raise NotImplementedError
