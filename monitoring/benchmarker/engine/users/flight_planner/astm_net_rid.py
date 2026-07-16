import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from functools import partial
from random import Random
from typing import Any

from monitoring.benchmarker.configurations.users import (
    ASTMDSSSelectionStrategy,
    ASTMNetRIDBehaviorSpecification,
    ASTMNetRIDISAPerFlightStrategySpecification,
)
from monitoring.benchmarker.engine.users.flight_planner.framework import (
    CompletedFlightAction,
    Flight,
    FlightAction,
    FlightActionType,
)
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.monitorlib.fetch.rid import ISA
from monitoring.monitorlib.geo import get_latlngrect_vertices
from monitoring.monitorlib.mutate.rid import ISAChange, delete_isa, put_isa
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources.astm.f3411.dss import (
    DSSInstance,
    DSSInstanceResource,
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID


class ASTMNetRIDHandler:
    user: VirtualUser

    dss_instances: list[DSSInstance]
    dss_selection_strategy: ASTMDSSSelectionStrategy

    isa_per_flight: ASTMNetRIDISAPerFlightStrategySpecification | None = None

    random: Random

    def __init__(
        self,
        behavior: ASTMNetRIDBehaviorSpecification,
        resource_pool: dict[ResourceID, Any],
        user: VirtualUser,
    ):
        self.user = user

        self.dss_instances = []
        for res_id in behavior.dss_pool:
            if res_id not in resource_pool:
                raise ValueError(
                    f"Resource '{res_id}' in astm_netrid_behavior.dss_pool not found in resource pool"
                )
            res = resource_pool[res_id]
            if isinstance(res, DSSInstancesResource):
                self.dss_instances.extend(res.dss_instances)
            elif isinstance(res, DSSInstanceResource):
                self.dss_instances.append(res.dss_instance)
            else:
                raise ValueError(
                    f"Resource '{res_id}' is not a uss_qualifier.resources.astm.f3411.dss.DSSInstanceResource nor uss_qualifier.resources.astm.f3411.dss.DSSInstancesResource"
                )

        if not self.dss_instances:
            raise ValueError(
                f"No NetRID DSS instances resolved from astm_netrid_behavior.dss_pool for user '{user.user_id}'"
            )

        if len(self.dss_instances) > 1:
            if "dss_selection_strategy" in behavior and behavior.dss_selection_strategy:
                self.dss_selection_strategy = behavior.dss_selection_strategy
            else:
                raise ValueError(
                    f"User `{user.user_id}` specified {len(self.dss_instances)} DSS instances but no dss_selection strategy"
                )
        else:
            self.dss_selection_strategy = ASTMDSSSelectionStrategy.First

        if self.dss_selection_strategy not in (
            ASTMDSSSelectionStrategy.First,
            ASTMDSSSelectionStrategy.Random,
        ):
            raise NotImplementedError(
                f"DSS selection strategy '{self.dss_selection_strategy}' not implemented"
            )

        if (
            "isa_per_flight" in behavior.isa_strategy
            and behavior.isa_strategy.isa_per_flight
        ):
            self.isa_per_flight = ASTMNetRIDISAPerFlightStrategySpecification(
                **behavior.isa_strategy.isa_per_flight
            )
            if "after_flight_end" not in self.isa_per_flight:
                self.isa_per_flight.after_flight_end = None
        else:
            raise NotImplementedError(
                f"No supported ISA strategy was specified in user `{user.user_id}` specification for astm_netrid_behavior.isa_strategy"
            )

        self.random = Random()

    def select_dss_instance(self) -> DSSInstance:
        if self.dss_selection_strategy == ASTMDSSSelectionStrategy.First:
            return self.dss_instances[0]
        elif self.dss_selection_strategy == ASTMDSSSelectionStrategy.Random:
            return self.random.choice(self.dss_instances)
        else:
            raise NotImplementedError(
                f"Unsupported DSS selection strategy `{self.dss_selection_strategy}`"
            )

    async def create_isa(self, flight: Flight, isa_id: str) -> list[FlightAction]:
        assert self.isa_per_flight  # This method is only called in this case

        new_actions: list[FlightAction] = []
        t0 = datetime.now(UTC)

        dss_instance = self.select_dss_instance()
        uss_base_url = make_fake_url()

        altitude_lower = flight.volumes.altitude_lower
        altitude_upper = flight.volumes.altitude_upper
        if not altitude_lower or not altitude_upper:
            raise ValueError("Altitude bounds for flight were not fully defined")

        # TODO: create ISA asynchronously
        isa_change: ISAChange = await self.user.run_sync_client_call(
            put_isa,
            area_vertices=get_latlngrect_vertices(flight.volumes.rect_bounds),
            alt_lo=altitude_lower.to_w84_m(),
            alt_hi=altitude_upper.to_w84_m(),
            start_time=flight.start_time,
            end_time=flight.end_time,
            uss_base_url=uss_base_url,
            isa_id=isa_id,
            rid_version=dss_instance.rid_version,
            utm_client=dss_instance.client,
            isa_version=None,
            participant_id=dss_instance.participant_id,
        )

        isa_success = isa_change.dss_query.success
        self.user.record_query(isa_change.dss_query.query, successful=isa_success)
        for notif in isa_change.notifications.values():
            self.user.record_query(notif.query)
        flight.completed_actions.append(
            CompletedFlightAction(
                type=FlightActionType.CreateISA,
                initiated_at=t0,
                success=isa_success,
            )
        )

        if isa_success and self.isa_per_flight.after_flight_end:
            new_actions.append(
                FlightAction(
                    timestamp=flight.end_time
                    + self.isa_per_flight.after_flight_end.timedelta,
                    flight_id=flight.id,
                    start=partial(
                        self.delete_isa,
                        flight,
                        isa_change.dss_query.isa,
                    ),
                    run_on_shutdown=True,
                )
            )

        return new_actions

    async def delete_isa(self, flight: Flight, isa: ISA) -> list[FlightAction]:
        t0 = datetime.now(UTC)
        dss_instance = self.select_dss_instance()

        del_success = False

        if isa:
            # TODO: delete ISA asynchronously
            del_change: ISAChange = await self.user.run_sync_client_call(
                delete_isa,
                isa_id=isa.id,
                isa_version=isa.version,
                rid_version=dss_instance.rid_version,
                utm_client=dss_instance.client,
                participant_id=dss_instance.participant_id,
            )

            del_success = del_change.dss_query.success
            self.user.record_query(del_change.dss_query.query, successful=del_success)
            for notif in del_change.notifications.values():
                self.user.record_query(notif.query)
            flight.completed_actions.append(
                CompletedFlightAction(
                    type=FlightActionType.DeleteISA,
                    initiated_at=t0,
                    success=del_success,
                )
            )

        return []

    def get_utm_actions(self, flight: Flight) -> Iterable[FlightAction]:
        if self.isa_per_flight:
            isa_id = str(uuid.uuid4())
            yield FlightAction(
                timestamp=flight.start_time
                - self.isa_per_flight.before_flight_start.timedelta,
                flight_id=flight.id,
                start=partial(
                    self.create_isa,
                    flight,
                    isa_id,
                ),
                run_on_shutdown=False,
            )
