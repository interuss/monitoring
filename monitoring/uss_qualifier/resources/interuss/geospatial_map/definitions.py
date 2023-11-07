from enum import Enum
from typing import List, Optional

from implicitdict import ImplicitDict
from monitoring.monitorlib.geotemporal import Volume4DTemplateCollection


class ExpectedFeatureCheckResult(str, Enum):
    Block = "Block"
    """When a service provider being tested as a geospatial map provider is queried for whether any features are present for the specified volumes that would cause the flight described in this feature check to be blocked, the service provider must respond affirmatively; responding negatively will cause a failed check."""

    Advise = "Advise"
    """When a service provider being tested as a geospatial map provider is queried for whether any features are present for the specified volumes that would provide an advisory to the viewer viewing a map relevant to the planning of the flight described in this feature check, the service provider must respond affirmatively; responding negatively will cause a failed check.  The service provider does not need to include the content or number of advisories in its response."""

    Neither = "Neither"
    """When a service provider being tested as a geospatial map provider is queried for whether any features matching the other criteria in this feature check and causing a “block” or “advise” per above are present with the specified criteria, the service provider must respond negatively; responding affirmatively will cause a failed check."""


class FeatureCheck(ImplicitDict):
    geospatial_check_id: str
    """Unique (within table) test step/row identifier."""

    requirement_ids: List[str]
    """Jurisdictional identifiers of the requirements this test step is evaluating."""

    description: str
    """Human-readable test step description to aid in the debugging and traceability."""

    operation_rule_set: Optional[str] = None
    """The set of operating rules (or rule set) under which the operation described in the feature check should be performed."""

    volumes: Volume4DTemplateCollection
    """Spatial and temporal definition of the areas the virtual user intends to fly in.

    A service provider is expected to provide geospatial features relevant to any of the entire area specified and for any of the entire time specified.
    """

    restriction_source: Optional[str] = None
    """Which source for geospatial features describing restrictions should be considered when looking for the expected outcome."""

    expected_result: ExpectedFeatureCheckResult
    """Expected outcome when checking map for features as described."""


class FeatureCheckTable(ImplicitDict):
    rows: List[FeatureCheck]
