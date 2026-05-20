import unittest

from monitoring.uss_qualifier.resources.definitions import (
    ResourceDeclaration,
    ResourceID,
)
from monitoring.uss_qualifier.resources.dev.test_modifier import (
    TestNumberGeneratorModifierSpecification,
    TestNumberGeneratorSpecification,
)
from monitoring.uss_qualifier.resources.resource import create_resources


class TestModifierResource(unittest.TestCase):
    def _build_number_generator_declaration(
        self, base_id
    ) -> dict[ResourceID, ResourceDeclaration]:
        return {
            "number_generator": ResourceDeclaration(
                resource_type="resources.dev.TestNumberGeneratorResource",
                specification=TestNumberGeneratorSpecification(base_id=base_id),
            )
        }

    def _build_modifier_declaration(
        self, base_id, shift_interval
    ) -> dict[ResourceID, ResourceDeclaration]:
        return {
            "number_generator": self._build_number_generator_declaration(base_id)[
                "number_generator"
            ],
            "modifier": ResourceDeclaration(
                resource_type="resources.dev.TestNumberGeneratorModifierResource",
                specification=TestNumberGeneratorModifierSpecification(
                    shift_interval=shift_interval
                ),
                dependencies={
                    "base_resource": "number_generator",
                },
            ),
        }

    def test_base_resource(self):
        """Test basic usage of the resource"""
        declaration = self._build_number_generator_declaration(42)

        resources = create_resources(declaration, "unittest", True)
        assert "number_generator" in resources

        resource = resources["number_generator"]

        assert resource.build_ids() == [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

    def test_base_resource_base_id(self):
        """Test that base id works as expected"""

        declaration = self._build_number_generator_declaration(52)

        resources = create_resources(declaration, "unittest", True)
        assert "number_generator" in resources

        resource = resources["number_generator"]

        assert resource.build_ids() == [52, 53, 54, 55, 56, 57, 58, 59, 60, 61]

    def test_modifier_resource(self):
        """Test basic usage of the resource modifier resource"""
        declaration = self._build_modifier_declaration(42, 10)

        resources = create_resources(declaration, "unittest", True)
        assert "modifier" in resources

        resource = resources["modifier"]

        assert resource.adjust(0).build_ids() == [
            42,
            43,
            44,
            45,
            46,
            47,
            48,
            49,
            50,
            51,
        ]
        assert resource.adjust(1).build_ids() == [
            52,
            53,
            54,
            55,
            56,
            57,
            58,
            59,
            60,
            61,
        ]

    def test_modifier_resource_shift(self):
        """Test shift usage of the resource modifier"""
        declaration = self._build_modifier_declaration(42, 20)

        resources = create_resources(declaration, "unittest", True)
        assert "modifier" in resources

        resource = resources["modifier"]

        assert resource.adjust(0).build_ids() == [
            42,
            43,
            44,
            45,
            46,
            47,
            48,
            49,
            50,
            51,
        ]
        assert resource.adjust(1).build_ids() == [
            62,
            63,
            64,
            65,
            66,
            67,
            68,
            69,
            70,
            71,
        ]
