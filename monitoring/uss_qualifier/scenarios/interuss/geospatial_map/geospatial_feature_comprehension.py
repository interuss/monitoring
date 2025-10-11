import arrow

from monitoring.monitorlib.clients.geospatial_info.client import (
    GeospatialInfoClient,
    GeospatialInfoError,
)
from monitoring.monitorlib.clients.geospatial_info.querying import (
    GeospatialFeatureCheck,
    GeospatialFeatureFilter,
    OperationalImpact,
    SelectionOutcome,
)
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.geospatial_info import (
    GeospatialInfoProviderResource,
)
from monitoring.uss_qualifier.resources.interuss.geospatial_map import (
    FeatureCheckTableResource,
)
from monitoring.uss_qualifier.resources.interuss.geospatial_map.definitions import (
    ExpectedFeatureCheckResult,
    FeatureCheckTable,
)
from monitoring.uss_qualifier.scenarios.documentation.definitions import (
    TestCheckDocumentation,
    TestStepDocumentation,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

_SUCCESSFUL_QUERY_CHECK_NAME = "Geospatial query succeeded"
_BLOCK_CHECK_NAME = "Blocking geospatial features present"
_ADVISE_CHECK_NAME = "Advisory geospatial features present"
_NEITHER_CHECK_NAME = "No blocking or advisory features present"
_CHECK_NAMES = {
    ExpectedFeatureCheckResult.Block: _BLOCK_CHECK_NAME,
    ExpectedFeatureCheckResult.Advise: _ADVISE_CHECK_NAME,
    ExpectedFeatureCheckResult.Neither: _NEITHER_CHECK_NAME,
}


class GeospatialFeatureComprehension(TestScenario):
    participant_id: ParticipantID
    geospatial_client: GeospatialInfoClient
    table: FeatureCheckTable

    def __init__(
        self,
        geospatial_info_provider: GeospatialInfoProviderResource,
        table: FeatureCheckTableResource,
    ):
        super().__init__()
        self.participant_id = geospatial_info_provider.participant_id
        self.geospatial_client = geospatial_info_provider.client
        self.table = table.table

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        times = {
            TimeDuringTest.StartOfTestRun: Time(context.start_time),
            TimeDuringTest.StartOfScenario: Time(arrow.utcnow().datetime),
        }

        self.begin_test_case("Map query")
        self._map_query(times)
        self.end_test_case()

        self.end_test_scenario()

    def _map_query(self, times: dict[TimeDuringTest, Time]):
        query_check = [
            c
            for c in self._current_case.steps[0].checks
            if c.name == _SUCCESSFUL_QUERY_CHECK_NAME
        ][0]
        for row in self.table.rows:
            if row.expected_result not in _CHECK_NAMES:
                raise NotImplementedError(
                    f"expected_result {row.expected_result} is not yet supported"
                )
            check_name = _CHECK_NAMES[row.expected_result]
            original_check = [
                c for c in self._current_case.steps[0].checks if c.name == check_name
            ][0]
            # Note that we are duck-typing a List[str] into a List[RequirementID] for applicable_requirements, but this
            # should be ok as the requirements are only used as strings from this point.
            check = TestCheckDocumentation(
                name=check_name,
                url=original_check.url,
                applicable_requirements=row.requirement_ids,
                has_todo=original_check.has_todo,
                severity=original_check.severity,
            )
            doc = TestStepDocumentation(
                name=row.geospatial_check_id,
                url=self._current_case.steps[0].url,
                checks=[query_check, check],
            )
            self.begin_dynamic_test_step(doc)
            if row.description:
                self.record_note(
                    f"{row.geospatial_check_id}.description", row.description
                )

            # Populate filter set
            filter_set = GeospatialFeatureFilter()

            times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
            concrete_volumes = [v.resolve(times) for v in row.volumes]
            filter_set.volumes4d = concrete_volumes

            if row.restriction_source:
                filter_set.restriction_source = row.restriction_source

            if row.operation_rule_set:
                filter_set.operation_rule_set = row.operation_rule_set

            if row.expected_result == ExpectedFeatureCheckResult.Block:
                filter_set.resulting_operational_impact = OperationalImpact.Block
            elif row.expected_result == ExpectedFeatureCheckResult.Advise:
                filter_set.resulting_operational_impact = OperationalImpact.Advise
            elif row.expected_result == ExpectedFeatureCheckResult.Neither:
                filter_set.resulting_operational_impact = (
                    OperationalImpact.BlockOrAdvise
                )
            else:
                raise ValueError(
                    f"GeospatialFeatureComprehension scenario is unable to perform an appropriate query for expected_result of {row.expected_result.value}"
                )

            feature_check = GeospatialFeatureCheck(filter_sets=[filter_set])

            # Perform query
            with self.check(_SUCCESSFUL_QUERY_CHECK_NAME, self.participant_id) as check:
                try:
                    resp = self.geospatial_client.query_geospatial_features(
                        [feature_check]
                    )
                except GeospatialInfoError as e:
                    for q in e.queries:
                        self.record_query(q)
                        check.record_failed(
                            summary="Geospatial info query failed",
                            details=str(e),
                            query_timestamps=[q.request.timestamp for q in e.queries],
                        )
                    self.end_test_step()
                    continue
                for q in resp.queries:
                    self.record_query(q)
                query_timestamps = [q.request.timestamp for q in resp.queries]
                if len(resp.results) != 1:
                    check.record_failed(
                        summary="Wrong number of results returned",
                        details=f"Expected exactly 1 geospatial info query result, but instead received {len(resp.results)}",
                        query_timestamps=query_timestamps,
                    )
                    self.end_test_step()
                    continue

            # Check whether the response was correct
            with self.check(
                _CHECK_NAMES[row.expected_result], self.participant_id
            ) as check:
                result = resp.results[0]
                if row.expected_result in (
                    ExpectedFeatureCheckResult.Block,
                    ExpectedFeatureCheckResult.Advise,
                ):
                    feature_type = (
                        "blocking"
                        if row.expected_result == ExpectedFeatureCheckResult.Block
                        else "advisory"
                    )
                    if result.features_selection_outcome != SelectionOutcome.Present:
                        details = f"Expected to find one or more {feature_type} geospatial features, but instead the query indicated {result.features_selection_outcome.value}"
                        if "message" in result and result.message:
                            details += f" with message '{result.message}'"
                        check.record_failed(
                            summary=f"Expected {feature_type} feature missing",
                            details=details,
                            query_timestamps=query_timestamps,
                        )
                elif row.expected_result == ExpectedFeatureCheckResult.Neither:
                    if result.features_selection_outcome != SelectionOutcome.Absent:
                        details = f"Expected to find no blocking or advisory geospatial features, but instead the query indicated {result.features_selection_outcome.value}"
                        if "message" in result and result.message:
                            details += f" with message '{result.message}'"
                        check.record_failed(
                            summary="Blocking and/or advisory geospatial features unexpectedly found",
                            details=details,
                            query_timestamps=query_timestamps,
                        )
                else:
                    raise ValueError(
                        f"GeospatialFeatureComprehension scenario is unable to test expected_result of {row.expected_result}"
                    )

            self.end_test_step()
