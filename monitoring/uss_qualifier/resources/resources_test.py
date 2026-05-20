import unittest

from monitoring.uss_qualifier.resources.definitions import (
    ResourceDeclaration,
    ResourceID,
)
from monitoring.uss_qualifier.resources.dev.test_modifier import (
    TestModifierModifierSpecification,
    TestModifierSpecification,
)
from monitoring.uss_qualifier.resources.resource import create_resources


class TestResourceModifier(unittest.TestCase):
    def _build_test_modifier_declaration(
        self, base_id
    ) -> dict[ResourceID, ResourceDeclaration]:
        return {
            "test": ResourceDeclaration(
                resource_type="resources.dev.TestModifierResource",
                specification=TestModifierSpecification(base_id=base_id),
            )
        }

    def _build_test_modifier_modifier_declaration(
        self, base_id, shift_interval
    ) -> dict[ResourceID, ResourceDeclaration]:
        return {
            "test": self._build_test_modifier_declaration(base_id)["test"],
            "test_modifier": ResourceDeclaration(
                resource_type="resources.dev.TestModifierModifierResource",
                specification=TestModifierModifierSpecification(
                    shift_interval=shift_interval
                ),
                dependencies={
                    "base_resource": "test",
                },
            ),
        }

    def test_base_resource(self):
        """Test basic usage of the resource"""
        declaration = self._build_test_modifier_declaration(42)

        resources = create_resources(declaration, "test", True)
        assert "test" in resources

        resource = resources["test"]

        assert resource.build_ids() == [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

    def test_base_resource_base_id(self):
        """Test that base id works as expected"""

        declaration = self._build_test_modifier_declaration(52)

        resources = create_resources(declaration, "test", True)
        assert "test" in resources

        resource = resources["test"]

        assert resource.build_ids() == [52, 53, 54, 55, 56, 57, 58, 59, 60, 61]

    def test_modifier_resource(self):
        """Test basic usage of the resource modifier"""
        declaration = self._build_test_modifier_modifier_declaration(42, 10)

        resources = create_resources(declaration, "test", True)
        assert "test_modifier" in resources

        resource = resources["test_modifier"]

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
        declaration = self._build_test_modifier_modifier_declaration(42, 20)

        resources = create_resources(declaration, "test", True)
        assert "test_modifier" in resources

        resource = resources["test_modifier"]

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
