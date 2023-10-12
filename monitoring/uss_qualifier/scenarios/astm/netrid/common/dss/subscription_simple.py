from datetime import timedelta

import arrow
import datetime

from monitoring.monitorlib import schema_validation
from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.rid import RIDVersion
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
    PendingCheck,
)
from monitoring.monitorlib.mutate.rid import ChangedSubscription

from typing import Dict


class SubscriptionSimple(GenericTestScenario):
    """Based on prober/rid/v2/test_subscription_validation.py from the legacy prober tool."""

    SUB_TYPE = register_resource_type(371, "Subscription")

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
    ):
        """

        Args:
            dss: dss to test
            id_generator: will let us generate specific identifiers
            isa: Service Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
        """
        super().__init__()
        # This is an UTMClientSession
        self._dss = dss.dss_instance
        self._dss_wrapper = DSSWrapper(self, self._dss)
        # TODO: the id_factory seems to generate static IDs:
        #  for creating different subscriptions this probably won't do.
        self._sub_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._isa = isa.specification

    def run(self):
        self.begin_test_scenario()

        self._setup_case()

        self.begin_test_case("Subscription Simple")
        self.begin_test_step("Subscription Simple")

        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        self._ensure_clean_workspace_step()

        self.end_test_case()

    def _clean_any_sub(self):
        with self.check(
            "Successful subscription query", [self._dss.participant_id]
        ) as check:
            fetched = self._dss_wrapper.search_subs(
                check, [vertex.as_s2sphere() for vertex in self._isa.footprint]
            )
        for sub_id in fetched.subscriptions.keys():
            with self.check(
                "Successful subscription deletion", [self._dss.participant_id]
            ) as check:
                self._dss_wrapper.cleanup_sub(check, sub_id=sub_id)

    def _ensure_clean_workspace_step(self):
        self.begin_test_step("Ensure clean workspace")

        self._clean_any_sub()

        self.end_test_step()

    def _simple_subscription_validation(self):
        # TODO
        pass

    def cleanup(self):
        self.begin_cleanup()

        self._clean_any_sub()

        self.end_cleanup()
