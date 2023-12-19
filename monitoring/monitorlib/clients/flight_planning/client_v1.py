import uuid
from typing import Optional

from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.flight_planning.v1 import api
from uas_standards.interuss.automated_testing.flight_planning.v1.constants import Scope

from monitoring.monitorlib.clients.flight_planning.client import (
    FlightPlannerClient,
)
from monitoring.monitorlib.clients.flight_planning.client import PlanningActivityError
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightInfo,
    FlightID,
    ExecutionStyle,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResponse,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResult,
    FlightPlanStatus,
)
from monitoring.monitorlib.clients.flight_planning.test_preparation import (
    TestPreparationActivityResponse,
)
from monitoring.monitorlib.fetch import query_and_describe, QueryType
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.uss_qualifier.configurations.configuration import ParticipantID


class V1FlightPlannerClient(FlightPlannerClient):
    _session: UTMClientSession

    def __init__(self, session: UTMClientSession, participant_id: ParticipantID):
        super(V1FlightPlannerClient, self).__init__(participant_id=participant_id)
        self._session = session

    def _inject(
        self,
        flight_plan_id: FlightID,
        flight_info: FlightInfo,
        execution_style: ExecutionStyle,
        additional_fields: Optional[dict] = None,
    ) -> PlanningActivityResponse:
        flight_plan = flight_info.to_flight_plan()
        req = api.UpsertFlightPlanRequest(
            flight_plan=flight_plan,
            execution_style=execution_style,
            request_id=str(uuid.uuid4()),
        )
        if additional_fields:
            for k, v in additional_fields.items():
                req[k] = v

        op = api.OPERATIONS[api.OperationID.UpsertFlightPlan]
        url = op.path.format(flight_plan_id=flight_plan_id)
        query = query_and_describe(
            self._session,
            op.verb,
            url,
            json=req,
            scope=Scope.Plan,
            participant_id=self.participant_id,
            query_type=QueryType.InterUSSFlightPlanningV1UpsertFlightPlan,
        )
        if query.status_code != 200 and query.status_code != 201:
            raise PlanningActivityError(
                f"Attempt to plan flight returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: api.UpsertFlightPlanResponse = ImplicitDict.parse(
                query.response.json, api.UpsertFlightPlanResponse
            )
        except ValueError as e:
            raise PlanningActivityError(
                f"Response to plan flight could not be parsed: {str(e)}", query
            )

        created_status = [
            FlightPlanStatus.Planned,
            FlightPlanStatus.OkToFly,
            FlightPlanStatus.OffNominal,
        ]
        if resp.planning_result == PlanningActivityResult.Completed:
            if resp.flight_plan_status in created_status:
                self.created_flight_ids.add(flight_plan_id)

        response = PlanningActivityResponse(
            flight_id=flight_plan_id,
            queries=[query],
            activity_result=resp.planning_result,
            flight_plan_status=resp.flight_plan_status,
            includes_advisories=resp.includes_advisories,
        )

        return response

    def try_plan_flight(
        self,
        flight_info: FlightInfo,
        execution_style: ExecutionStyle,
        additional_fields: Optional[dict] = None,
    ) -> PlanningActivityResponse:
        return self._inject(
            str(uuid.uuid4()), flight_info, execution_style, additional_fields
        )

    def try_update_flight(
        self,
        flight_id: FlightID,
        updated_flight_info: FlightInfo,
        execution_style: ExecutionStyle,
        additional_fields: Optional[dict] = None,
    ) -> PlanningActivityResponse:
        return self._inject(
            flight_id, updated_flight_info, execution_style, additional_fields
        )

    def try_end_flight(
        self, flight_id: FlightID, execution_style: ExecutionStyle
    ) -> PlanningActivityResponse:
        if execution_style != ExecutionStyle.IfAllowed:
            raise NotImplementedError(
                "Only IfAllowed execution style is currently allowed"
            )
        op = api.OPERATIONS[api.OperationID.DeleteFlightPlan]
        url = op.path.format(flight_plan_id=flight_id)
        query = query_and_describe(
            self._session,
            op.verb,
            url,
            scope=Scope.Plan,
            participant_id=self.participant_id,
            query_type=QueryType.InterUSSFlightPlanningV1DeleteFlightPlan,
        )
        if query.status_code != 200:
            raise PlanningActivityError(
                f"Attempt to delete flight plan returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: api.DeleteFlightPlanResponse = ImplicitDict.parse(
                query.response.json, api.DeleteFlightPlanResponse
            )
        except ValueError as e:
            raise PlanningActivityError(
                f"Response to delete flight plan could not be parsed: {str(e)}", query
            )
        self.created_flight_ids.discard(flight_id)
        response = PlanningActivityResponse(
            flight_id=flight_id,
            queries=[query],
            activity_result=resp.planning_result,
            flight_plan_status=resp.flight_plan_status,
        )
        return response

    def report_readiness(self) -> TestPreparationActivityResponse:
        op = api.OPERATIONS[api.OperationID.GetStatus]
        query = query_and_describe(
            self._session,
            op.verb,
            op.path,
            scope=Scope.DirectAutomatedTest,
            participant_id=self.participant_id,
            query_type=QueryType.InterUSSFlightPlanningV1GetStatus,
        )
        if query.status_code != 200:
            raise PlanningActivityError(
                f"Attempt to get interface status returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: api.StatusResponse = ImplicitDict.parse(
                query.response.json, api.StatusResponse
            )
        except ValueError as e:
            raise PlanningActivityError(
                f"Response to get interface status could not be parsed: {str(e)}", query
            )

        if resp.status == api.StatusResponseStatus.Ready:
            errors = []
        elif resp.status == api.StatusResponseStatus.Starting:
            errors = ["Flight planning v1 interface is still starting (not ready)"]
        else:
            errors = [f"Unrecognized status '{resp.status}'"]

        return TestPreparationActivityResponse(errors=errors, queries=[query])

    def clear_area(self, area: Volume4D) -> TestPreparationActivityResponse:
        req = api.ClearAreaRequest(
            request_id=str(uuid.uuid4()), extent=area.to_interuss_scd_api()
        )

        op = api.OPERATIONS[api.OperationID.ClearArea]
        query = query_and_describe(
            self._session,
            op.verb,
            op.path,
            json=req,
            scope=Scope.DirectAutomatedTest,
            participant_id=self.participant_id,
            query_type=QueryType.InterUSSFlightPlanningV1ClearArea,
        )
        if query.status_code != 200:
            raise PlanningActivityError(
                f"Attempt to clear area returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: api.ClearAreaResponse = ImplicitDict.parse(
                query.response.json, api.ClearAreaResponse
            )
        except ValueError as e:
            raise PlanningActivityError(
                f"Response to clear area could not be parsed: {str(e)}", query
            )
        if resp.outcome.success:
            errors = None
        else:
            errors = [resp.outcome.message]

        return TestPreparationActivityResponse(errors=errors, queries=[query])

    def get_base_url(self):
        return self._session.get_prefix_url()
