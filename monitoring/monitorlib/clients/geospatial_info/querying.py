from enum import Enum
from typing import List, Optional

from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.interuss.automated_testing.geospatial_map.v1 import (
    api as geospatial_map_api,
)

from monitoring.monitorlib.fetch import Query
from monitoring.monitorlib.geo import LatLngPoint
from monitoring.monitorlib.geotemporal import Volume4D


class OperationalImpact(str, Enum):
    """The specified outcome if a user attempted to plan a flight."""

    Block = "Block"
    """The geospatial feature would cause rejection of that flight (the USS would decline to plan the flight)."""

    Advise = "Advise"
    """The geospatial feature would cause the USS to accompany a successful flight plan (if the flight was successfully planned) with an advisory or condition provided to the operator."""

    BlockOrAdvise = "BlockOrAdvise"
    """The geospatial feature would cause one of 'Block' or 'Advise' to be be true."""


class GeospatialFeatureFilter(ImplicitDict):
    """Filters to select only a subset of geospatial features.  Only geospatial features which are applicable to all specified criteria within this filter set should be selected."""

    # TODO: Add position

    volumes4d: Optional[List[Volume4D]]
    """If specified, only select geospatial features at least partially intersecting one or more of these volumes."""

    # TODO: Add after & before

    restriction_source: Optional[str]
    """If specified, only select geospatial features originating from the named source.  The acceptable values for this field will be established by the test designers and will generally be used to limit responses to only the intended datasets under test even when the USS may have more additional geospatial features from other sources that may otherwise be relevant."""

    operation_rule_set: Optional[str]
    """If specified, only select geospatial features that would be relevant when planning an operation under the specified rule set.  The acceptable values for this field will be established by the test designers and will generally correspond to sets of rules under which the system under test plans operations."""

    resulting_operational_impact: Optional[OperationalImpact]
    """If specified, only select geospatial features that would cause the specified outcome if a user attempted to plan a flight applicable to all the other criteria in this filter set."""

    def to_geospatial_map(self) -> geospatial_map_api.GeospatialFeatureFilterSet:
        result = geospatial_map_api.GeospatialFeatureFilterSet()
        if "volumes4d" in self and self.volumes4d:
            result.volumes4d = [v.to_geospatial_map_api() for v in self.volumes4d]
        if "restriction_source" in self and self.restriction_source:
            result.restriction_source = self.restriction_source
        if "operation_rule_set" in self and self.operation_rule_set:
            result.operation_rule_set = self.operation_rule_set
        if "resulting_operational_impact" in self and self.resulting_operational_impact:
            result.resulting_operational_impact = (
                geospatial_map_api.GeospatialFeatureFilterSetResultingOperationalImpact(
                    self.resulting_operational_impact
                )
            )
        return result


class GeospatialFeatureCheck(ImplicitDict):
    filter_sets: Optional[List[GeospatialFeatureFilter]]
    """Select geospatial features which match any of the specified filter sets."""

    def to_geospatial_map(self) -> geospatial_map_api.GeospatialMapCheck:
        return geospatial_map_api.GeospatialMapCheck(
            filter_sets=[fs.to_geospatial_map() for fs in self.filter_sets]
        )


class SelectionOutcome(str, Enum):
    """Indication of whether one or more applicable geospatial features were selected."""

    Present = "Present"
    """One or more applicable geospatial features were selected."""

    Absent = "Absent"
    """No applicable geospatial features were selected."""

    UnsupportedFilter = "UnsupportedFilter"
    """Applicable geospatial features could not be selected because one or more filter criteria are not supported by the USS."""

    Error = "Error"
    """An error or condition not enumerated above occurred."""


class GeospatialFeatureCheckResult(ImplicitDict):
    features_selection_outcome: SelectionOutcome
    """Indication of whether one or more applicable geospatial features were selected according to the selection criteria of the corresponding check."""

    message: Optional[str]
    """A human-readable description of why the unsuccessful `features_selection_outcome` was reported.  Should only be populated when appropriate according to the value of the `features_selection_outcome` field."""


class GeospatialFeatureQueryResponse(ImplicitDict):
    queries: List[Query]
    """Queries used to accomplish this activity."""

    results: List[GeospatialFeatureCheckResult]
    """Responses to each of the `checks` in the request.  The number of entries in this array should match the number of entries in the `checks` field of the request."""
