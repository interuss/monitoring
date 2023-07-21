from typing import List

from monitoring.uss_qualifier.scenarios.interuss.evaluation_scenario import (
    ReportEvaluationScenario,
)

from monitoring.uss_qualifier.resources.interuss.report import TestSuiteReportResource
from monitoring.uss_qualifier.resources.netrid import (
    NetRIDServiceProviders,
    NetRIDObserversResource,
)
from monitoring.uss_qualifier.resources.netrid.observers import RIDSystemObserver
from monitoring.uss_qualifier.resources.netrid.service_providers import (
    NetRIDServiceProvider,
)

# TODO: implement me


class AggregateChecks(ReportEvaluationScenario):
    _service_providers: List[NetRIDServiceProvider]
    _observers: List[RIDSystemObserver]

    def __init__(
        self,
        report_resource: TestSuiteReportResource,
        service_providers: NetRIDServiceProviders,
        observers: NetRIDObserversResource,
    ):
        super().__init__(report_resource)
        self._service_providers = service_providers.service_providers
        self._observers = observers.observers

    def run(self):
        self.begin_test_scenario()
        self.record_note("dummy", "TODO: this is a dummy implementation")

        self.begin_test_case("Dummy")
        self.begin_test_step("Dummy")

        with self.check("Dummy", []) as check:
            self.record_note("nb_sps", f"{len(self._service_providers)}")
            self.record_note("nb_obs", f"{len(self._observers)}")

        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()

    def cleanup(self):
        self.skip_cleanup()
