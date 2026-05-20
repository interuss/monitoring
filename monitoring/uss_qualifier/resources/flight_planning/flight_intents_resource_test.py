import unittest

from monitoring.monitorlib.geo import area_of_latlngrect
from monitoring.uss_qualifier.resources.definitions import (
    ResourceDeclaration,
    ResourceID,
)
from monitoring.uss_qualifier.resources.modifiers import (
    GeospatialModifierSpecification,
)
from monitoring.uss_qualifier.resources.resource import (
    create_resources,
)


class TestFlightIntentsGeospatialModifier(unittest.TestCase):
    def _build_declarations(self) -> dict[ResourceID, ResourceDeclaration]:
        return {
            "flight_intents": ResourceDeclaration(
                resource_type="resources.flight_planning.FlightIntentsResource",
                specification={
                    "file": {
                        "path": "file://./test_data/che/flight_intents/general_flight_auth_flights.yaml",
                    },
                },
            ),
            "flight_intents_modifier": ResourceDeclaration(
                resource_type="resources.flight_planning.FlightIntentsModifier",
                specification=GeospatialModifierSpecification(),
                dependencies={
                    "base_resource": "flight_intents",
                },
            ),
        }

    def test_overlap_only_for_same_index(self):
        resources = create_resources(self._build_declarations(), "test", True)
        modifier = resources["flight_intents_modifier"]

        extents = [modifier.adjust(i).get_extents() for i in range(11)]
        base_area = area_of_latlngrect(extents[0].to_latlngrect())

        for i in range(11):
            for j in range(11):
                overlap = area_of_latlngrect(
                    extents[i].to_latlngrect().intersection(extents[j].to_latlngrect())
                )
                if i == j:
                    assert (
                        overlap > 0.99 * base_area
                    ), (  # Use 99% to compensate for errors
                        f"index {i}: self-overlap area {overlap:.2f}m² "
                        f"expected ~{base_area:.2f}m²"
                    )
                else:
                    assert (
                        overlap < 0.01 * base_area
                    ), (  # Use 1% to compensate for errors
                        f"indices {i},{j}: unexpected overlap area {overlap:.2f}m²"
                    )
