from typing import List

from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.netrid import NetRIDObserversResource
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class MSLAltitude(TestScenario):
    _ussps: List[ParticipantID]

    def __init__(self, observers: NetRIDObserversResource):
        super().__init__()
        self._ussps = [obs.participant_id for obs in observers.observers]

    def run(self, context):
        self.begin_test_scenario(context)

        self.begin_test_case("UAS observations evaluation")

        self.begin_test_step("Find nominal behavior report")
        # TODO: Find test report for NetRID nominal behavior scenario
        self.end_test_step()

        self.begin_test_step("Evaluate UAS observations")
        # TODO: Examine observation queries in test report to see if MSL was present
        # TODO: When MSL is present, verify that its value matches injected altitude above ellipsoid
        self.end_test_step()

        self.end_test_case()

        self.end_test_scenario()
