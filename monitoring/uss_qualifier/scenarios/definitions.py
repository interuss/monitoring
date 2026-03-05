from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.definitions import ResourceID

TestScenarioTypeName = str
"""This plain string represents a type of test scenario, expressed as a Python class name qualified relative to the
`uss_qualifier` module.

Note that equality between different TestScenarioTypeNames (whether they refer to the same type of test scenario) should
be determined via are_scenario_types_equal as multiple TestScenarioTypeNames may resolve to the same test scenario type.
"""


class TestScenarioDeclaration(ImplicitDict):
    scenario_type: TestScenarioTypeName
    """Type of test scenario."""

    resources: dict[ResourceID, ResourceID] | None
    """Mapping of the ID a resource in the test scenario -> the ID a resource is known by in the parent test suite.

    The additional argument to concrete test scenario constructor <key> is supplied by the parent suite resource <value>.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "resources" not in self:
            self.resources = {}
