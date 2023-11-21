import copy
import datetime
from typing import Optional, List, Dict, Any

import arrow
import s2sphere

from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3411 import v19, v22a

from monitoring.monitorlib.fetch import query_and_describe
from monitoring.monitorlib.mutate.rid import ChangedISA
from monitoring.monitorlib.rid import RIDVersion
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources import VerticesResource
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss import utils
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario


class ISAValidation(GenericTestScenario):
    """Based on prober/rid/v2/test_isa_validation.py from the legacy prober tool."""

    ISA_TYPE = register_resource_type(368, "ISA")

    _huge_are: List[s2sphere.LatLng]

    create_isa_path: str

    write_scope: str

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
        problematically_big_area: VerticesResource,
    ):
        super().__init__()
        self._dss = (
            dss.dss_instance
        )  # TODO: delete once _delete_isa_if_exists updated to use dss_wrapper
        self._dss_wrapper = DSSWrapper(self, dss.dss_instance)
        self._isa_id = id_generator.id_factory.make_id(ISAValidation.ISA_TYPE)
        self._isa_version: Optional[str] = None
        self._isa = isa.specification

        now = arrow.utcnow().datetime
        self._isa_start_time = self._isa.shifted_time_start(now)
        self._isa_end_time = self._isa.shifted_time_end(now)
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]

        self._huge_area = [
            v.as_s2sphere() for v in problematically_big_area.specification.vertices
        ]

        if self._dss.rid_version == RIDVersion.f3411_19:
            self.create_isa_path = v19.api.OPERATIONS[
                v19.api.OperationID.CreateSubscription
            ].path
            self.write_scope = v19.constants.Scope.Write
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            self.create_isa_path = v22a.api.OPERATIONS[
                v22a.api.OperationID.CreateSubscription
            ].path
            self.write_scope = v22a.constants.Scope.ServiceProvider
        else:
            ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self._setup_case()

        self.begin_test_case("ISA Validation")
        self.begin_test_step("ISA Validation")

        (create_isa_url, json_body) = self._isa_huge_area_check()

        self._isa_empty_vertices_check()
        self._isa_start_time_in_past()
        self._isa_start_time_after_time_end()
        self._isa_vertices_are_valid()

        self._isa_missing_outline(create_isa_url, json_body)
        self._isa_missing_volume(create_isa_url, json_body)

        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        def _ensure_clean_workspace_step():
            self.begin_test_step("Ensure clean workspace")

            self._delete_isa_if_exists()

            self.end_test_step()

        _ensure_clean_workspace_step()

        self.end_test_case()

    def _delete_isa_if_exists(self):
        utils.delete_isa_if_exists(
            self,
            isa_id=self._isa_id,
            rid_version=self._dss.rid_version,
            session=self._dss.client,
            participant_id=self._dss_wrapper.participant_id,
            ignore_base_url=self._isa.base_url,
        )

    def _isa_huge_area_check(self) -> (str, Dict[str, Any]):
        """Returns the request's URL and json payload for subsequently re-using it.

        It is of the following form (note that v19 and v22a have slight differences):

        "extents": {
            "volume": {
                "outline_polygon": {
                        "vertices": [],
                },
                "altitude_lower": 20.0,
                "altitude_upper": 400.0,
            },
            "time_start": <timestamp>,
            "time_end": <timestamp>,
        },
        "uss_base_url": <base_url>,
        """

        with self.check("ISA huge area", [self._dss_wrapper.participant_id]) as check:
            q = self._dss_wrapper.put_isa_expect_response_code(
                check=check,
                expected_error_codes={400},
                area_vertices=self._huge_area,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
                start_time=self._isa_start_time,
                end_time=self._isa_end_time,
                uss_base_url=self._isa.base_url,
                isa_id=self._isa_id,
                isa_version=self._isa_version,
            )

        return q.dss_query.query.request.url, q.dss_query.query.request.json

    def _isa_empty_vertices_check(self):

        with self.check(
            "ISA empty vertices", [self._dss_wrapper.participant_id]
        ) as check:
            self._dss_wrapper.put_isa_expect_response_code(
                check=check,
                expected_error_codes={400},
                area_vertices=[],
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
                start_time=self._isa_start_time,
                end_time=self._isa_end_time,
                uss_base_url=self._isa.base_url,
                isa_id=self._isa_id,
                isa_version=self._isa_version,
            )

    def _isa_start_time_in_past(self):
        time_start = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        time_end = time_start + datetime.timedelta(minutes=60)

        with self.check(
            "ISA start time in the past", [self._dss_wrapper.participant_id]
        ) as check:
            self._dss_wrapper.put_isa_expect_response_code(
                check=check,
                expected_error_codes={400},
                area_vertices=self._isa_area,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
                start_time=time_start,
                end_time=time_end,
                uss_base_url=self._isa.base_url,
                isa_id=self._isa_id,
                isa_version=self._isa_version,
            )

    def _isa_start_time_after_time_end(self):
        with self.check(
            "ISA start time after end time", [self._dss_wrapper.participant_id]
        ) as check:
            self._dss_wrapper.put_isa_expect_response_code(
                check=check,
                expected_error_codes={400},
                area_vertices=self._isa_area,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
                start_time=self._isa.time_end.datetime,
                end_time=self._isa.time_start.datetime,
                uss_base_url=self._isa.base_url,
                isa_id=self._isa_id,
                isa_version=self._isa_version,
            )

    def _isa_vertices_are_valid(self):
        INVALID_VERTICES: List[s2sphere.LatLng] = [
            s2sphere.LatLng.from_degrees(lat=130, lng=-23),
            s2sphere.LatLng.from_degrees(lat=130, lng=-24),
            s2sphere.LatLng.from_degrees(lat=132, lng=-24),
            s2sphere.LatLng.from_degrees(lat=132, lng=-23),
        ]

        with self.check(
            "ISA vertices are valid", [self._dss_wrapper.participant_id]
        ) as check:
            self._dss_wrapper.put_isa_expect_response_code(
                check=check,
                expected_error_codes={400},
                area_vertices=INVALID_VERTICES,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
                start_time=self._isa.time_start.datetime,
                end_time=self._isa.time_end.datetime,
                uss_base_url=self._isa.base_url,
                isa_id=self._isa_id,
                isa_version=self._isa_version,
            )

    def _isa_missing_outline(self, create_isa_url: str, json_body: Dict[str, Any]):
        payload = copy.deepcopy(json_body)
        if self._dss.rid_version == RIDVersion.f3411_19:
            del payload["extents"]["spatial_volume"]["footprint"]
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            del payload["extents"]["volume"]["outline_polygon"]

        with self.check(
            "ISA missing outline", [self._dss_wrapper.participant_id]
        ) as check:
            q = query_and_describe(
                client=self._dss.client,
                verb="PUT",
                url=create_isa_url,
                scope=self.write_scope,
                json=payload,
            )
            if self._dss.rid_version == RIDVersion.f3411_19:
                rid_query = ChangedISA(v19_query=q)
            elif self._dss.rid_version == RIDVersion.f3411_22a:
                rid_query = ChangedISA(v22a_query=q)
            else:
                raise ValueError(f"Unknown RID version: {self._dss.rid_version}")

            rid_query.set_participant_id(self._dss_wrapper.participant_id)

            self._dss_wrapper.handle_query_result(
                check=check,
                q=rid_query,
                fail_msg="ISA Creation with missing outline has unexpected result code",
                required_status_code={400},
                severity=Severity.High,
            )

    def _isa_missing_volume(self, create_isa_url: str, json_body: Dict[str, Any]):
        payload = copy.deepcopy(json_body)
        if self._dss.rid_version == RIDVersion.f3411_19:
            del payload["extents"]["spatial_volume"]
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            del payload["extents"]["volume"]

        with self.check(
            "ISA missing volume", [self._dss_wrapper.participant_id]
        ) as check:
            q = query_and_describe(
                client=self._dss.client,
                verb="PUT",
                url=create_isa_url,
                scope=self.write_scope,
                json=payload,
            )
            if self._dss.rid_version == RIDVersion.f3411_19:
                rid_query = ChangedISA(v19_query=q)
            elif self._dss.rid_version == RIDVersion.f3411_22a:
                rid_query = ChangedISA(v22a_query=q)
            else:
                raise ValueError(f"Unknown RID version: {self._dss.rid_version}")

            rid_query.set_participant_id(self._dss_wrapper.participant_id)

            self._dss_wrapper.handle_query_result(
                check=check,
                q=rid_query,
                fail_msg="ISA Creation with missing outline has unexpected result code",
                required_status_code={400},
                severity=Severity.High,
            )

    def _isa_missing_extents(self, create_isa_url: str, json_body: Dict[str, Any]):
        payload = copy.deepcopy(json_body)
        del payload["extents"]

        with self.check(
            "ISA missing extents", [self._dss_wrapper.participant_id]
        ) as check:
            q = query_and_describe(
                client=self._dss.client,
                verb="PUT",
                url=create_isa_url,
                scope=self.write_scope,
                json=payload,
            )
            if self._dss.rid_version == RIDVersion.f3411_19:
                rid_query = ChangedISA(v19_query=q)
            elif self._dss.rid_version == RIDVersion.f3411_22a:
                rid_query = ChangedISA(v22a_query=q)
            else:
                raise ValueError(f"Unknown RID version: {self._dss.rid_version}")

            self._dss_wrapper.handle_query_result(
                check=check,
                q=rid_query,
                fail_msg="ISA Creation with missing outline has unexpected result code",
                required_status_code={400},
                severity=Severity.High,
            )

    def cleanup(self):
        self.begin_cleanup()

        self._delete_isa_if_exists()

        self.end_cleanup()
