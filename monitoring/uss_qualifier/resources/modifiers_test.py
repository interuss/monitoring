import unittest

from monitoring.monitorlib.geo import area_of_latlngrect
from monitoring.uss_qualifier.resources.definitions import (
    ResourceDeclaration,
    ResourceID,
)
from monitoring.uss_qualifier.resources.dev.test_modifier import (
    TestSquareSpecification,
)
from monitoring.uss_qualifier.resources.modifiers import (
    GeospatialModifierSpecification,
)
from monitoring.uss_qualifier.resources.resource import create_resources


class TestGeospatialModifier(unittest.TestCase):
    def _build_declarations(self) -> dict[ResourceID, ResourceDeclaration]:
        return {
            "square": ResourceDeclaration(
                resource_type="resources.dev.TestSquareResource",
                specification=TestSquareSpecification(lat_center=46.5, lng_center=6.5),
            ),
            "square_modifier": ResourceDeclaration(
                resource_type="resources.dev.TestSquareModifier",
                specification=GeospatialModifierSpecification(),
                dependencies={
                    "base_resource": "square",
                },
            ),
        }

    def test_overlap_only_for_same_index(self):
        resources = create_resources(self._build_declarations(), "test", True)
        modifier = resources["square_modifier"]

        extents = [modifier.adjust(i).get_extents() for i in range(11)]
        square_area = (
            resources["square"].SQUARE_SIDE_M * resources["square"].SQUARE_SIDE_M
        )

        for i in range(11):
            for j in range(11):
                rect_i = extents[i].to_latlngrect()
                rect_j = extents[j].to_latlngrect()
                overlap = area_of_latlngrect(rect_i.intersection(rect_j))
                if i == j:
                    assert (
                        overlap > 0.99 * square_area
                    ), (  # Use 99% to compensate for errors
                        f"index {i}: self-overlap area {overlap:.2f}m² "
                        f"expected ~{square_area:.2f}m²"
                    )
                else:
                    assert (
                        overlap < 0.01 * square_area
                    ), (  # Use 1% to compensate for errors
                        f"indices {i},{j}: unexpected overlap area {overlap:.2f}m²"
                    )
