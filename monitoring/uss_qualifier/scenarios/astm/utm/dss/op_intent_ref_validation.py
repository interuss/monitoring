import json
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

from uas_standards.astm.f3548.v21.api import (
    OPERATIONS,
    ChangeOperationalIntentReferenceResponse,
    EntityID,
    OperationalIntentState,
    OperationID,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryType, query_and_describe
from monitoring.monitorlib.geo import Circle, Polygon
from monitoring.monitorlib.ids import register_resource_type
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.volume import VolumeResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OIRValidation(TestScenario):
    OIR_TYPE = register_resource_type(406, "Operational Intent Reference")

    _dss: DSSInstance
    _oir_id: EntityID

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        client_identity: ClientIdentityResource,
        planning_area: PlanningAreaResource,
        problematically_big_area: VolumeResource,
    ):
        super().__init__()
        self._dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "create and delete operational intent references"
            }
        )
        self._pid = [self._dss.participant_id]
        self._oir_id = id_generator.id_factory.make_id(self.OIR_TYPE)
        self._expected_manager = client_identity.subject()
        self._planning_area = planning_area
        self._problematically_big_area = problematically_big_area

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self.begin_test_step("Cleanup OIRs")
        self._clean_all_oirs()
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Creation validation")
        self.begin_test_step("Attempt creation with invalid parameters")
        self._attempt_creation_with_invalid_parameters()
        self.end_test_step()
        self.begin_test_step("Attempt creation with invalid extents")
        self._attempt_creation_with_invalid_extents()
        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()

    def _valid_params(
        self, time_start: datetime | None = None, time_end: datetime | None = None
    ) -> dict[str, Any]:
        params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.specification.get_base_url(),
            time_start=time_start or datetime.now() - timedelta(seconds=10),
            time_end=time_end or datetime.now() + timedelta(minutes=20),
            subscription_id=None,
            implicit_sub_base_url=self._planning_area.specification.get_base_url(),
        )
        return json.loads(json.dumps(params))

    def _attempt_invalid_creation(
        self,
        check_name: str,
        params: dict[str, Any],
        oir_id: str | None = None,
        expected_codes: tuple[int, ...] = (400,),
    ):
        op = OPERATIONS[OperationID.CreateOperationalIntentReference]
        q = query_and_describe(
            self._dss.client,
            op.verb,
            op.path.format(entityid=oir_id or self._oir_id),
            QueryType.F3548v21DSSCreateOperationalIntentReference,
            self._dss.participant_id,
            scope=Scope.StrategicCoordination,
            json=params,
        )
        self.record_query(q)
        with self.check(check_name, self._pid) as check:
            if q.status_code not in expected_codes:
                check.record_failed(
                    summary=f"Expected {' or '.join(str(c) for c in expected_codes)}, got {q.status_code}",
                    query_timestamps=[q.request.timestamp],
                )
        if q.status_code == 201:
            oir = q.parse_json_result(
                ChangeOperationalIntentReferenceResponse
            ).operational_intent_reference
            if oir.ovn:
                test_step_fragments.remove_op_intent(self, self._dss, oir.id, oir.ovn)

    def _attempt_creation_with_invalid_parameters(self):
        self._attempt_invalid_creation(
            "Invalid ID is rejected", self._valid_params(), oir_id="not_uuid_format"
        )

    def _attempt_creation_with_invalid_extents(self):
        params = self._valid_params()
        params["extents"] = params["extents"][0]
        self._attempt_invalid_creation(
            "Extents not provided as a list are rejected", params
        )

        params = self._valid_params()
        del params["extents"][0]["time_start"]
        self._attempt_invalid_creation(
            "Extents missing start time are rejected", params
        )

        params = self._valid_params()
        del params["extents"][0]["time_end"]
        self._attempt_invalid_creation("Extents missing end time are rejected", params)

        time_start = datetime.now() - timedelta(days=1)
        params = self._valid_params(time_start, time_start + timedelta(minutes=60))
        self._attempt_invalid_creation(
            "Extents ending in the past are rejected", params
        )

        time_start = datetime.now() + timedelta(minutes=20)
        params = self._valid_params(time_start, time_start + timedelta(minutes=60))
        extent = params["extents"][0]
        extent["time_start"], extent["time_end"] = (
            extent["time_end"],
            extent["time_start"],
        )
        self._attempt_invalid_creation(
            "Extents starting after they end are rejected", params
        )

        params = self._valid_params()
        params["extents"][0]["time_end"]["format"] = "RFC3330"
        self._attempt_invalid_creation(
            "Extents with invalid time format are rejected", params
        )

        planning_area_polygon = Polygon.from_latlng_coords(
            self._planning_area.resolved_volume4d_with_times(
                None, None
            ).volume.s2_vertices()
        )

        params = self._valid_params()
        polygon = deepcopy(planning_area_polygon)
        polygon.vertices[0].lat = 110
        params["extents"][0]["volume"].pop("outline_circle", None)
        params["extents"][0]["volume"]["outline_polygon"] = polygon
        self._attempt_invalid_creation(
            "Extents with invalid coordinates are rejected", params
        )

        params = self._valid_params()
        params["extents"][0]["volume"].pop("outline_circle", None)
        params["extents"][0]["volume"]["outline_polygon"] = Polygon(
            vertices=self._problematically_big_area.specification.vertices()
        )
        self._attempt_invalid_creation(
            "Extents with a too large area are rejected",
            params,
            expected_codes=(400, 413),
        )

        params = self._valid_params()
        vertex = planning_area_polygon.vertices[0]
        params["extents"][0]["volume"]["outline_polygon"] = planning_area_polygon
        params["extents"][0]["volume"]["outline_circle"] = Circle.from_meters(
            vertex.lat, vertex.lng, 300
        )
        self._attempt_invalid_creation(
            "Extents with both circle and polygon outlines are rejected", params
        )

    def _clean_all_oirs(self):
        vol = self._planning_area.resolved_volume4d_with_times(None, None)
        test_step_fragments.cleanup_active_oirs(
            self,
            self._dss,
            vol.to_f3548v21(),
            self._expected_manager,
        )
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)

    def cleanup(self):
        self.begin_cleanup()
        self._clean_all_oirs()
        self.end_cleanup()
