from types import MappingProxyType
from typing import Dict, Optional

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.fileio import FileReference
from monitoring.uss_qualifier.resources.definitions import ResourceID


class TestScenarioDeclaration(ImplicitDict):
    scenario_type: FileReference
    """Type/location of test scenario.  Usually expressed as the class name of the scenario module-qualified relative to the `uss_qualifier` folder"""

    resources: Optional[Dict[ResourceID, ResourceID]]
    """Mapping of the ID a resource in the test scenario -> the ID a resource is known by in the parent test suite.

    The additional argument to concrete test scenario constructor <key> is supplied by the parent suite resource <value>.
    """

    def __init__(self, *args, **kwargs):
        super(TestScenarioDeclaration, self).__init__(*args, **kwargs)
        if "resources" not in self:
            self.resources = {}
