from abc import ABC, abstractmethod
from typing import List, Optional, Union

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


class PlanningActivityError(QueryError):
    pass


class FlightPlannerClient(ABC):
    """Client to interact with a USS as a user performing flight planning activities and as the test director preparing for tests involving flight planning activities."""

    # ===== Emulation of user actions =====

    @abstractmethod
    def try_plan_flight(
        self, flight_info: FlightInfo, execution_style: ExecutionStyle
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
