from datetime import UTC, datetime

from monitoring.uss_qualifier.resources.dev import NoOpResource
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class NoOp(TestScenario):
    def __init__(self, noop_config: NoOpResource):
        super().__init__()
        self.sleep_secs = noop_config.sleep_secs

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Sleep")
        self.begin_test_step("Sleep")

        self.record_note(
            "Start time",
            f"Starting at {datetime.now(UTC).isoformat()}Z, sleeping for {self.sleep_secs}s...",
        )

        self.sleep(self.sleep_secs, "the no-op scenario sleeps for the specified time")

        self.record_note("End time", f"Ending at {datetime.now(UTC).isoformat()}Z.")

        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()
