from typing import Dict, Optional

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.fileio import FileReference
from monitoring.uss_qualifier.resources.definitions import ResourceID


TestScenarioTypeName = str
"""This plain string represents a type of test scenario, expressed as a Python class name qualified relative to the `uss_qualifier` module"""


class TestScenarioDeclaration(ImplicitDict):
    scenario_type: TestScenarioTypeName
    """Type of test scenario."""

    resources: Optional[Dict[ResourceID, ResourceID]]
    """Mapping of the ID a resource in the test scenario -> the ID a resource is known by in the parent test suite.

    The additional argument to concrete test scenario constructor <key> is supplied by the parent suite resource <value>.
    """

    def __init__(self, *args, **kwargs):
        super(TestScenarioDeclaration, self).__init__(*args, **kwargs)
        if "resources" not in self:
            self.resources = {}
