from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from monitoring.benchmarker.engine.users.framework import Action
from monitoring.monitorlib.geotemporal import Volume4DCollection


class FlightID(str):
    pass


@dataclass(order=True, kw_only=True)
class FlightAction(Action):
    flight_id: FlightID | None = field(default=None, compare=False)


class FlightActionType(StrEnum):
    CompleteFlight = "complete_flight"
    """The virtual user finished flying the virtual physical flight.
    
    Success for this action does not necessarily imply UTM actions were all successful."""

    CreateISA = "astm_netrid_behavior.create_isa"
    DeleteISA = "astm_netrid_behavior.delete_isa"


@dataclass
class CompletedFlightAction:
    type: FlightActionType
    initiated_at: datetime
    success: bool


@dataclass
class Flight:
    id: FlightID
    volumes: Volume4DCollection
    completed_actions: list[CompletedFlightAction] = field(default_factory=lambda: [])

    @property
    def earliest_action_initiated_at(self) -> datetime | None:
        if not self.completed_actions:
            return None
        return min(action.initiated_at for action in self.completed_actions)

    @property
    def start_time(self) -> datetime:
        t = self.volumes.time_start
        if not t:
            raise ValueError(f"The volumes of flight {id} do not have a start time")
        return t.datetime

    @property
    def end_time(self) -> datetime:
        t = self.volumes.time_end
        if not t:
            raise ValueError(f"The volumes of flight {id} do not have an end time")
        return t.datetime

    @property
    def successful(self) -> bool:
        return all(action.success for action in self.completed_actions)

    async def complete(self) -> list[FlightAction]:
        self.completed_actions.append(
            CompletedFlightAction(
                type=FlightActionType.CompleteFlight,
                initiated_at=self.start_time,
                success=True,
            )
        )
        return []


class FlightGenerator(ABC):
    @abstractmethod
    def generate_flight(self, previous_flight_end: datetime) -> Flight:
        raise NotImplementedError()
