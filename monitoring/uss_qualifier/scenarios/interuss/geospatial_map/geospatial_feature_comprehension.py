from datetime import datetime
from typing import Dict

import arrow

from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.uss_qualifier.resources.interuss.geospatial_map import (
    FeatureCheckTableResource,
)
from monitoring.uss_qualifier.resources.interuss.geospatial_map.definitions import (
    FeatureCheckTable,
    ExpectedFeatureCheckResult,
)
from monitoring.uss_qualifier.scenarios.documentation.definitions import (
    TestStepDocumentation,
    TestCheckDocumentation,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

_BLOCK_CHECK_NAME = "Blocking geospatial features present"
_ADVISE_CHECK_NAME = "Advisory geospatial features present"
_NEITHER_CHECK_NAME = "No blocking or advisory features present"
_CHECK_NAMES = {
    ExpectedFeatureCheckResult.Block: _BLOCK_CHECK_NAME,
    ExpectedFeatureCheckResult.Advise: _ADVISE_CHECK_NAME,
    ExpectedFeatureCheckResult.Neither: _NEITHER_CHECK_NAME,
}


class GeospatialFeatureComprehension(TestScenario):
    table: FeatureCheckTable

    def __init__(
        self,
        table: FeatureCheckTableResource,  # TODO: Add geospatial map provider resource
    ):
        super().__init__()
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

    def _map_query(self, times: Dict[TimeDuringTest, Time]):
        for row in self.table.rows:
            if row.expected_result not in _CHECK_NAMES:
                raise NotImplementedError(
                    f"expected_result {row.expected_result} is not yet supported"
                )
            check_name = _CHECK_NAMES[row.expected_result]
            check_url = [
                c.url
                for c in self._current_case.steps[0].checks
                if c.name == check_name
            ][0]
            # Note that we are duck-typing a List[str] into a List[RequirementID] for applicable_requirements, but this
            # should be ok as the requirements are only used as strings from this point.
            check = TestCheckDocumentation(
                name=check_name,
                url=check_url,
                applicable_requirements=row.requirement_ids,
                has_todo=False,
            )
            doc = TestStepDocumentation(
                name=row.geospatial_check_id,
                url=self._current_case.steps[0].url,
                checks=[check],
            )
            self.begin_dynamic_test_step(doc)

            if row.volumes:
                times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
                concrete_volumes = [v.resolve(times) for v in row.volumes]

                # TODO: Query USSs under test
                self.record_note(
                    "map_query",
                    f"TODO: Query USSs for features from {row.restriction_source} for {row.operation_rule_set} that cause {row.expected_result} from {concrete_volumes[0].time_start} to {concrete_volumes[0].time_end}",
                )

            with self.check(
                _CHECK_NAMES[row.expected_result], []
            ) as check:  # TODO: Add participant_id
                pass  # TODO: check USS query results

            self.end_test_step()
