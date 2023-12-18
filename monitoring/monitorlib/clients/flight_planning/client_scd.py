import uuid
from typing import Dict, Optional
from implicitdict import ImplicitDict
from monitoring.monitorlib.clients.flight_planning.client import (
    FlightPlannerClient,
    PlanningActivityError,
)
from monitoring.monitorlib.clients.flight_planning.test_preparation import (
    TestPreparationActivityResponse,
)
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_api
from uas_standards.interuss.automated_testing.scd.v1 import (
    constants as scd_api_constants,
)

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightInfo,
    FlightID,
    ExecutionStyle,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResponse,
    PlanningActivityResult,
    FlightPlanStatus,
)
from monitoring.monitorlib.fetch import query_and_describe
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.uss_qualifier.configurations.configuration import ParticipantID


class SCDFlightPlannerClient(FlightPlannerClient):
    SCD_SCOPE = scd_api_constants.Scope.Inject
    _session: UTMClientSession
    _plan_statuses: Dict[FlightID, FlightPlanStatus]

    def __init__(self, session: UTMClientSession, participant_id: ParticipantID):
        super(SCDFlightPlannerClient, self).__init__(participant_id=participant_id)
        self._session = session
        self._plan_statuses = {}

    def _inject(
        self,
        flight_id: FlightID,
        flight_info: FlightInfo,
        execution_style: ExecutionStyle,
        additional_fields: Optional[dict] = None,
    ) -> PlanningActivityResponse:
        if execution_style != ExecutionStyle.IfAllowed:
            raise PlanningActivityError(
                f"Legacy scd automated testing API only supports {ExecutionStyle.IfAllowed} actions; '{execution_style}' is not supported"
            )

        req = flight_info.to_scd_inject_flight_request()

        if "astm_f3548_21" in flight_info and flight_info.astm_f3548_21:
            priority = flight_info.astm_f3548_21.priority
        else:
            priority = 0

        operational_intent = scd_api.OperationalIntentTestInjection(
            state=req.operational_intent.state,
            priority=priority,
            volumes=req.operational_intent.volumes,
            off_nominal_volumes=req.operational_intent.off_nominal_volumes,
        )

        kwargs = {"operational_intent": operational_intent}
        if (
            "uspace_flight_authorisation" in flight_info
            and flight_info.uspace_flight_authorisation
        ):
            kwargs["flight_authorisation"] = ImplicitDict.parse(
                flight_info.uspace_flight_authorisation, scd_api.FlightAuthorisationData
            )
        req = scd_api.InjectFlightRequest(**kwargs)
        if additional_fields:
            for k, v in additional_fields.items():
                req[k] = v

        op = scd_api.OPERATIONS[scd_api.OperationID.InjectFlight]
        url = op.path.format(flight_id=flight_id)
        query = query_and_describe(
            self._session, op.verb, url, json=req, scope=self.SCD_SCOPE
        )
        if query.status_code != 200 and query.status_code != 201:
            raise PlanningActivityError(
                f"Attempt to plan flight returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: scd_api.InjectFlightResponse = ImplicitDict.parse(
                query.response.json, scd_api.InjectFlightResponse
            )
        except ValueError as e:
            raise PlanningActivityError(
                f"Response to plan flight could not be parsed: {str(e)}", query
            )

        old_state = (
            self._plan_statuses[flight_id]
            if flight_id in self._plan_statuses
            else FlightPlanStatus.NotPlanned
        )
        response = PlanningActivityResponse(
            flight_id=flight_id,
            queries=[query],
            activity_result={
                scd_api.InjectFlightResponseResult.Planned: PlanningActivityResult.Completed,
                scd_api.InjectFlightResponseResult.ReadyToFly: PlanningActivityResult.Completed,
                scd_api.InjectFlightResponseResult.ConflictWithFlight: PlanningActivityResult.Rejected,
                scd_api.InjectFlightResponseResult.Rejected: PlanningActivityResult.Rejected,
                scd_api.InjectFlightResponseResult.Failed: PlanningActivityResult.Failed,
                scd_api.InjectFlightResponseResult.NotSupported: PlanningActivityResult.NotSupported,
            }[resp.result],
            flight_plan_status={
                scd_api.InjectFlightResponseResult.Planned: FlightPlanStatus.Planned,
                scd_api.InjectFlightResponseResult.ReadyToFly: FlightPlanStatus.OkToFly,
                scd_api.InjectFlightResponseResult.ConflictWithFlight: old_state,
                scd_api.InjectFlightResponseResult.Rejected: old_state,
                scd_api.InjectFlightResponseResult.Failed: old_state,
                scd_api.InjectFlightResponseResult.NotSupported: old_state,
            }[resp.result],
        )

        created_status = [
            FlightPlanStatus.Planned,
            FlightPlanStatus.OkToFly,
            FlightPlanStatus.OffNominal,
        ]
        if response.activity_result == PlanningActivityResult.Completed:
            if response.flight_plan_status in created_status:
                self.created_flight_ids.add(flight_id)

        self._plan_statuses[flight_id] = response.flight_plan_status
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
        op = scd_api.OPERATIONS[scd_api.OperationID.DeleteFlight]
        url = op.path.format(flight_id=flight_id)
        query = query_and_describe(self._session, op.verb, url, scope=self.SCD_SCOPE)
        if query.status_code != 200:
            raise PlanningActivityError(
                f"Attempt to delete flight returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: scd_api.DeleteFlightResponse = ImplicitDict.parse(
                query.response.json, scd_api.DeleteFlightResponse
            )
        except ValueError as e:
            raise PlanningActivityError(
                f"Response to delete flight could not be parsed: {str(e)}", query
            )

        old_state = (
            self._plan_statuses[flight_id]
            if flight_id in self._plan_statuses
            else FlightPlanStatus.NotPlanned
        )
        response = PlanningActivityResponse(
            flight_id=flight_id,
            queries=[query],
            activity_result={
                scd_api.DeleteFlightResponseResult.Closed: PlanningActivityResult.Completed,
                scd_api.DeleteFlightResponseResult.Failed: PlanningActivityResult.Failed,
            }[resp.result],
            flight_plan_status={
                scd_api.DeleteFlightResponseResult.Closed: FlightPlanStatus.Closed,
                scd_api.DeleteFlightResponseResult.Failed: old_state,
            }[resp.result],
        )
        if resp.result == scd_api.DeleteFlightResponseResult.Closed:
            del self._plan_statuses[flight_id]
            self.created_flight_ids.discard(flight_id)

        else:
            self._plan_statuses[flight_id] = response.flight_plan_status
        return response

    def report_readiness(self) -> TestPreparationActivityResponse:
        op = scd_api.OPERATIONS[scd_api.OperationID.GetStatus]
        query = query_and_describe(
            self._session, op.verb, op.path, scope=self.SCD_SCOPE
        )
        if query.status_code != 200:
            raise PlanningActivityError(
                f"Attempt to get interface status returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: scd_api.StatusResponse = ImplicitDict.parse(
                query.response.json, scd_api.StatusResponse
            )
        except ValueError as e:
            raise PlanningActivityError(
                f"Response to get interface status could not be parsed: {str(e)}", query
            )

        if resp.status == scd_api.StatusResponseStatus.Ready:
            errors = []
        elif resp.status == scd_api.StatusResponseStatus.Starting:
            errors = ["SCD flight planning interface is still starting (not ready)"]
        else:
            errors = [f"Unrecognized status '{resp.status}'"]

        # Note that checking capabilities is not included because the SCD flight planning interface is deprecated and does not warrant full support

        return TestPreparationActivityResponse(errors=errors, queries=[query])

    def clear_area(self, area: Volume4D) -> TestPreparationActivityResponse:
        req = scd_api.ClearAreaRequest(
            request_id=str(uuid.uuid4()), extent=area.to_interuss_scd_api()
        )

        op = scd_api.OPERATIONS[scd_api.OperationID.ClearArea]
        query = query_and_describe(
            self._session, op.verb, op.path, json=req, scope=self.SCD_SCOPE
        )
        if query.status_code != 200:
            raise PlanningActivityError(
                f"Attempt to clear area returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: scd_api.ClearAreaResponse = ImplicitDict.parse(
                query.response.json, scd_api.ClearAreaResponse
            )
        except ValueError as e:
            raise PlanningActivityError(
                f"Response to clear area could not be parsed: {str(e)}", query
            )

        if resp.outcome.success:
            errors = None
        else:
            errors = [f"[{resp.outcome.timestamp}]: {resp.outcome.message}"]

        return TestPreparationActivityResponse(errors=errors, queries=[query])

    def get_base_url(self):
        return self._session.get_prefix_url()
