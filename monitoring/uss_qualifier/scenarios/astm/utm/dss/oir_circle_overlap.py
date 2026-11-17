"""Test discovery of registered circular OIRs through the DSS search API."""

from datetime import UTC, datetime, timedelta
from itertools import product
from math import cos, radians, sin

import s2sphere
from shapely.geometry import Point, Polygon
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    PutOperationalIntentReferenceParameters,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geo import EARTH_RADIUS_M, Circle, flatten
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.ids import register_resource_type
from monitoring.monitorlib.s2 import cell_of
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.oir import (
    crud as oir_fragments,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class FixtureUnavailable(Exception):
    """No valid cross-boundary circular fixture fits in the planning area."""


class OIRCircleOverlap(TestScenario):
    """Check discovery of OIRs through genuinely overlapping circular queries."""

    OIR_TYPE = register_resource_type(
        407, "Circular overlap operational intent reference"
    )

    # S2 defines difficult query geometry, not the DSS's indexing contract.
    # The API must return every OIR that genuinely intersects the query.
    CELL_LEVEL = 13
    OIR_RADIUS_M = 300.0
    QUERY_RADIUS_M = 1.0
    # The 1m query is wholly across an S2 vertex, not across a shared edge.
    QUERY_CORNER_DISTANCE_M = 2.5
    # Tilting the OIR centerline produces a narrow but positive overlap
    # with the diagonal cell, without assuming a particular DSS index.
    CENTER_TILT_DEG = -30.0
    TRUE_OVERLAP_M = 0.1
    OVERLAP_TOLERANCE_M = 0.001
    PLANNING_AREA_MARGIN_M = 1.0
    SAMPLE_FRACTIONS = tuple(i / 8 for i in range(1, 8))

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
    ):
        super().__init__()
        self._dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "create and query operational intent references"
            }
        )
        self._participants = [self._dss.participant_id]
        self._oir_id = id_generator.id_factory.make_id(self.OIR_TYPE)
        self._planning_area = planning_area

    @staticmethod
    def _move(origin, tangent, meters):
        theta = meters / EARTH_RADIUS_M
        return (origin * cos(theta) + tangent * sin(theta)).normalize()

    @classmethod
    def _cell(cls, point):
        ll = s2sphere.LatLng.from_point(point)
        return cell_of(ll.lat().degrees, ll.lng().degrees, cls.CELL_LEVEL)

    @classmethod
    def _circle_in_cell(cls, cell, center, radius_m):
        if not cell.contains(center):
            return False
        clearance = sin(radius_m / EARTH_RADIUS_M)
        for edge in range(4):
            a = cell.get_vertex(edge)
            b = cell.get_vertex((edge + 1) % 4)
            inward = a.cross_prod(b).normalize()
            if inward.dot_prod(cell.get_center()) < 0:
                inward = -inward
            if inward.dot_prod(center) <= clearance:
                return False
        return True

    @staticmethod
    def _reference(volume):
        if volume.outline_circle is not None:
            return volume.outline_circle.center.as_s2sphere()
        if volume.outline_polygon is not None and volume.outline_polygon.vertices:
            return volume.outline_polygon.vertex_average().as_s2sphere()
        raise FixtureUnavailable("Planning Area needs a circle or polygon outline")

    @classmethod
    def _fits(cls, center, radius_m, volume, reference):
        margin = cls.PLANNING_AREA_MARGIN_M
        if volume.outline_circle is not None:
            planning_center = volume.outline_circle.center.as_s2sphere().to_point()
            distance = center.angle(planning_center) * EARTH_RADIUS_M
            return (
                distance + radius_m + margin < volume.outline_circle.radius.in_meters()
            )

        polygon = Polygon(
            flatten(reference, vertex.as_s2sphere())
            for vertex in volume.outline_polygon.vertices
        )
        if not polygon.is_valid or polygon.is_empty:
            raise FixtureUnavailable("Planning Area polygon is invalid")
        candidate = Point(*flatten(reference, s2sphere.LatLng.from_point(center)))
        return polygon.buffer(-(radius_m + margin)).covers(candidate)

    @staticmethod
    def _altitudes(area):
        low = area.altitude_lower_wgs84_m() if area.altitude_lower else None
        high = area.altitude_upper_wgs84_m() if area.altitude_upper else None
        if low is None:
            low = high - 90.0 if high is not None else 30.0
        if high is None:
            high = low + 90.0
        if low >= high:
            raise FixtureUnavailable("Planning Area has no positive altitude span")
        return low + (high - low) / 4, high - (high - low) / 4

    @staticmethod
    def _circle(center, radius_m):
        ll = s2sphere.LatLng.from_point(center)
        return Circle.from_meters(ll.lat().degrees, ll.lng().degrees, radius_m)

    def _fixtures(self, volume):
        """Find four narrow circle overlaps across diagonal S2 cell corners."""
        bounds = self._planning_area.get_extents()
        planning_reference = self._reference(volume)
        cells = {}
        for fx, fy in product(self.SAMPLE_FRACTIONS, repeat=2):
            sample = s2sphere.LatLng.from_degrees(
                bounds.lat_min + (bounds.lat_max - bounds.lat_min) * fx,
                bounds.lng_min + (bounds.lng_max - bounds.lng_min) * fy,
            ).to_point()
            cell_id = self._cell(sample)
            cells[cell_id.id()] = cell_id

        fixtures = []
        for source_id in sorted(cells.values(), key=lambda c: c.id()):
            source_cell = s2sphere.Cell(source_id)
            source_center = source_cell.get_center()
            edge_neighbors = set(source_id.get_edge_neighbors())
            for corner_index in range(4):
                vertex = source_cell.get_vertex(corner_index)
                inward = (
                    source_center - vertex * source_center.dot_prod(vertex)
                ).normalize()
                query_center = self._move(vertex, -inward, self.QUERY_CORNER_DISTANCE_M)
                query_cell_id = self._cell(query_center)
                # Exclude the source cell and its edge-neighbors: this is
                # specifically a corner-crossing search, not an edge case.
                if query_cell_id == source_id or query_cell_id in edge_neighbors:
                    continue
                if not self._circle_in_cell(
                    s2sphere.Cell(query_cell_id), query_center, self.QUERY_RADIUS_M
                ) or not self._fits(
                    query_center, self.QUERY_RADIUS_M, volume, planning_reference
                ):
                    continue

                # Work in the tangent plane at the query center. This keeps
                # the center separation controlled in spherical distance.
                toward_corner = (
                    vertex - query_center * query_center.dot_prod(vertex)
                ).normalize()
                sideways = query_center.cross_prod(toward_corner).normalize()
                tilt = radians(self.CENTER_TILT_DEG)
                toward_source = (
                    toward_corner * cos(tilt) + sideways * sin(tilt)
                ).normalize()
                oir_center = self._move(
                    query_center,
                    toward_source,
                    self.OIR_RADIUS_M + self.QUERY_RADIUS_M - self.TRUE_OVERLAP_M,
                )
                if self._cell(oir_center) != source_id or not self._fits(
                    oir_center, self.OIR_RADIUS_M, volume, planning_reference
                ):
                    continue
                overlap = (
                    self.OIR_RADIUS_M
                    + self.QUERY_RADIUS_M
                    - oir_center.angle(query_center) * EARTH_RADIUS_M
                )
                # Validate real-circle intersection; do not test membership
                # against any particular polygon approximation or index.
                if abs(overlap - self.TRUE_OVERLAP_M) > self.OVERLAP_TOLERANCE_M:
                    continue

                fixtures.append(
                    (
                        self._circle(oir_center, self.OIR_RADIUS_M),
                        self._circle(query_center, self.QUERY_RADIUS_M),
                    )
                )
                self.record_note(
                    "fixture_constructed",
                    f"source_cell={source_id.id()}; query_cell={query_cell_id.id()}; "
                    f"corner={corner_index}; overlap_m={overlap:.3f}",
                )
                if len(fixtures) == 4:
                    return fixtures

        raise FixtureUnavailable(
            f"PlanningAreaResource {bounds} cannot fit four true-circle "
            "S2 corner overlap cases"
        )

    def _check_found(self, name, circle, start, end, alt0, alt1):
        query = Volume4D.from_values(
            t0=start,
            t1=end,
            alt0=alt0,
            alt1=alt1,
            circle=circle,
        ).to_f3548v21()

        with self.check(name, self._participants) as check:
            try:
                found, response = self._dss.find_op_intent(query)
                self.record_query(response)
                if self._oir_id not in {oir.id for oir in found}:
                    check.record_failed(
                        summary="Overlapping OIR was missing",
                        details=f"OIR id={self._oir_id}; query={circle}",
                        query_timestamps=[response.request.timestamp],
                    )
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="Search failed",
                    details=f"HTTP {e.cause_status_code}: {e.msg}",
                    query_timestamps=e.query_timestamps,
                )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        area = self._planning_area.resolved_volume4d_with_times(None, None).volume
        alt0, alt1 = self._altitudes(area)
        fixtures = self._fixtures(area)

        self.begin_test_case("Setup")
        self.begin_test_step("Clear previous test OIR")
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Overlapping circular OIR is discoverable")
        start = datetime.now(UTC) + timedelta(minutes=5)
        end = start + timedelta(minutes=60)

        for oir_circle, boundary_query in fixtures:
            self.begin_test_step("Create circular OIR")
            params = PutOperationalIntentReferenceParameters(
                extents=[
                    Volume4D.from_values(
                        t0=start,
                        t1=end,
                        alt0=alt0,
                        alt1=alt1,
                        circle=oir_circle,
                    ).to_f3548v21()
                ],
                key=[],
                state=OperationalIntentState.Accepted,
                uss_base_url=make_fake_url(),
                subscription_id=None,
            )
            created_oir, _, _ = oir_fragments.create_oir_query(
                scenario=self,
                dss=self._dss,
                oir_id=self._oir_id,
                oir_params=params,
            )
            self.end_test_step()

            self.begin_test_step("Discover boundary-overlapping OIR")
            self._check_found(
                "Boundary overlap is discoverable",
                boundary_query,
                start,
                end,
                alt0,
                alt1,
            )
            self.end_test_step()

            self.begin_test_step("Ordinary contained circle discovers OIR")
            contained_query = Circle.from_meters(
                oir_circle.center.lat,
                oir_circle.center.lng,
                self.OIR_RADIUS_M / 2,
            )
            self._check_found(
                "Ordinary contained circle discovers OIR",
                contained_query,
                start,
                end,
                alt0,
                alt1,
            )
            self.end_test_step()

            self.begin_test_step("Delete circular OIR")
            assert created_oir.ovn is not None
            oir_fragments.delete_oir_query(
                scenario=self,
                dss=self._dss,
                oir_id=self._oir_id,
                ovn=created_oir.ovn,
            )
            self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def cleanup(self):
        self.begin_cleanup()
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_cleanup()
