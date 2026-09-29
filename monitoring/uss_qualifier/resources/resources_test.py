import unittest

import pytest

from monitoring.uss_qualifier.resources.definitions import (
    ResourceDeclaration,
    ResourceID,
)
from monitoring.uss_qualifier.resources.dev.test_modifier import (
    NumberGeneratorModifierSpecification,
    NumberGeneratorResource,
    NumberGeneratorSpecification,
    TestSquareSpecification,
)
from monitoring.uss_qualifier.resources.geospatial import (
    TriangularCascadeSoutheastSpecification,
)
from monitoring.uss_qualifier.resources.resource import (
    Resource,
    SupportedKeysNotSpecifiedError,
    create_resources,
)


class GenericContainerResource[T: Resource](Resource[NumberGeneratorSpecification]):
    dependency: T
    optional_dependency: NumberGeneratorResource | None

    def __init__(
        self,
        specification: NumberGeneratorSpecification,
        resource_origin: str,
        dependency: T,
        optional_dependency: NumberGeneratorResource | None = None,
    ):
        super().__init__(specification, resource_origin)
        self.dependency = dependency
        self.optional_dependency = optional_dependency


class TestModifierResource(unittest.TestCase):
    def _build_number_generator_declaration(
        self, base_id
    ) -> dict[ResourceID, ResourceDeclaration]:
        return {
            "number_generator": ResourceDeclaration(
                resource_type="resources.dev.NumberGeneratorResource",
                specification=NumberGeneratorSpecification(base_id=base_id),
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
                resource_type="resources.dev.NumberGeneratorModifierResource",
                specification=NumberGeneratorModifierSpecification(
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

        with pytest.raises(SupportedKeysNotSpecifiedError):
            resource.provide_resource_for(key=0)

        with pytest.raises(SupportedKeysNotSpecifiedError):
            resource.provide_resource_for(index="foo")

        assert resource.provide_resource_for(index=0).build_ids() == [
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
        assert resource.provide_resource_for(index=1).build_ids() == [
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

        assert resource.provide_resource_for(index=0).build_ids() == [
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
        assert resource.provide_resource_for(index=1).build_ids() == [
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

    def test_generic_resource_instantiation_and_is_or_inherits(self):
        """Test generic ResourceTypeName instantiation, dependency validation, and is_or_inherits."""
        declarations = {
            "square": ResourceDeclaration(
                resource_type="resources.dev.TestSquareResource",
                specification=TestSquareSpecification(lat_center=46.5, lng_center=6.5),
            ),
            "generic_modifier": ResourceDeclaration(
                resource_type="resources.geospatial.TriangularCascadeSoutheastResource[resources.dev.TestSquareResource]",
                specification=TriangularCascadeSoutheastSpecification(
                    meters_east_margin=100, meters_north_margin=100
                ),
                dependencies={"base_resource": "square"},
            ),
            "concrete_modifier": ResourceDeclaration(
                resource_type="resources.dev.TestSquareModifier",
                specification=TriangularCascadeSoutheastSpecification(
                    meters_east_margin=100, meters_north_margin=100
                ),
                dependencies={"base_resource": "square"},
            ),
            "nested_container": ResourceDeclaration(
                resource_type="resources.resources_test.GenericContainerResource[resources.geospatial.TriangularCascadeSoutheastResource[resources.dev.TestSquareResource]]",
                specification=NumberGeneratorSpecification(base_id=1),
                dependencies={"dependency": "generic_modifier"},
            ),
        }
        resources = create_resources(declarations, "unittest", True)

        for mod_key in ("generic_modifier", "concrete_modifier"):
            mod = resources[mod_key]
            assert mod.is_or_inherits(
                "resources.geospatial.TriangularCascadeSoutheastResource[resources.dev.TestSquareResource]"
            )
            assert mod.is_or_inherits(
                "resources.geospatial.TriangularCascadeSoutheastResource[resources.geospatial.GeospatialResource]"
            )
            assert mod.is_or_inherits(
                "resources.resource.ResourceProvidingResource[resources.dev.TestSquareResource]"
            )
            assert not mod.is_or_inherits(
                "resources.geospatial.TriangularCascadeSoutheastResource[resources.flight_planning.FlightIntentsResource]"
            )
            assert not mod.is_or_inherits(
                "resources.geospatial.TriangularCascadeSoutheastResource[resources.dev.NumberGeneratorResource]"
            )

        nested = resources["nested_container"]
        assert nested.is_or_inherits(
            "resources.resources_test.GenericContainerResource[resources.geospatial.TriangularCascadeSoutheastResource[resources.geospatial.GeospatialResource]]"
        )
        assert not nested.is_or_inherits(
            "resources.resources_test.GenericContainerResource[resources.geospatial.TriangularCascadeSoutheastResource[resources.flight_planning.FlightIntentsResource]]"
        )

        # Mismatched dependency type should fail validation
        bad_declarations = {
            "number_generator": self._build_number_generator_declaration(1)[
                "number_generator"
            ],
            "bad_container": ResourceDeclaration(
                resource_type="resources.resources_test.GenericContainerResource[resources.dev.TestSquareResource]",
                specification=NumberGeneratorSpecification(base_id=1),
                dependencies={"dependency": "number_generator"},
            ),
        }
        with pytest.raises(ValueError):
            create_resources(bad_declarations, "unittest", True)

    def test_optional_dependencies_and_base_resource_pool(self):
        """Test optional resource dependencies (`?` and default `= None`) and `base_resource_pool`."""
        base_pool = create_resources(
            self._build_number_generator_declaration(10), "base_pool", True
        )

        declarations = {
            "omitted_optional": ResourceDeclaration(
                resource_type="resources.resources_test.GenericContainerResource[resources.dev.NumberGeneratorResource]",
                specification=NumberGeneratorSpecification(base_id=1),
                dependencies={"dependency": "number_generator"},
            ),
            "absent_optional": ResourceDeclaration(
                resource_type="resources.resources_test.GenericContainerResource[resources.dev.NumberGeneratorResource]",
                specification=NumberGeneratorSpecification(base_id=2),
                dependencies={
                    "dependency": "number_generator",
                    "optional_dependency": "nonexistent_generator?",
                },
            ),
            "present_optional": ResourceDeclaration(
                resource_type="resources.resources_test.GenericContainerResource[resources.dev.NumberGeneratorResource]",
                specification=NumberGeneratorSpecification(base_id=3),
                dependencies={
                    "dependency": "number_generator",
                    "optional_dependency": "number_generator?",
                },
            ),
        }
        resources = create_resources(
            declarations, "unittest", True, base_resource_pool=base_pool
        )

        assert resources["omitted_optional"].dependency is base_pool["number_generator"]
        assert resources["omitted_optional"].optional_dependency is None
        assert resources["absent_optional"].optional_dependency is None
        assert (
            resources["present_optional"].optional_dependency
            is base_pool["number_generator"]
        )

        # Using `?` on a required parameter without default must raise ValueError
        invalid_optional_declarations = {
            "invalid_optional": ResourceDeclaration(
                resource_type="resources.resources_test.GenericContainerResource[resources.dev.NumberGeneratorResource]",
                specification=NumberGeneratorSpecification(base_id=4),
                dependencies={"dependency": "nonexistent_generator?"},
            )
        }
        with pytest.raises(ValueError):
            create_resources(
                invalid_optional_declarations,
                "unittest",
                True,
                base_resource_pool=base_pool,
            )
