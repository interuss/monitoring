import ipaddress
import socket
from typing import List, Optional
from urllib.parse import urlparse

from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.dev.test_exclusions import (
    TestExclusionsResource,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3548.v21.api import Volume4D, Volume3D, Polygon, LatLngPoint
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstancesResource,
    DSSInstanceResource,
    DSSInstance,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class DSSInteroperability(TestScenario):

    _dss_primary: DSSInstance
    _dss_others: List[DSSInstance]
    _allow_private_addresses: bool = False

    _valid_search_area: Volume4D

    def __init__(
        self,
        primary_dss_instance: DSSInstanceResource,
        all_dss_instances: DSSInstancesResource,
        planning_area: PlanningAreaResource,
        test_exclusions: Optional[TestExclusionsResource] = None,
    ):
        super().__init__()
        scopes = {
            Scope.StrategicCoordination: "search for operational intent references to verify DSS is reachable"
        }
        self._dss_primary = primary_dss_instance.get_instance(scopes)
        self._dss_others = [
            dss.get_instance(scopes)
            for dss in all_dss_instances.dss_instances
            if not dss.is_same_as(primary_dss_instance)
        ]

        self._valid_search_area = Volume4D(volume=planning_area.specification.volume)

        if test_exclusions is not None:
            self._allow_private_addresses = test_exclusions.allow_private_addresses

    def run(self, context: ExecutionContext):

        self.begin_test_scenario(context)

        self.begin_test_case("Prerequisites")

        self.begin_test_step("Test environment requirements")
        self._test_env_reqs()
        self.end_test_step()

        self.end_test_case()

        self.end_test_scenario()

    def _test_env_reqs(self):
        for dss in [self._dss_primary] + self._dss_others:
            with self.check(
                "DSS instance is publicly addressable", [dss.participant_id]
            ) as check:
                parsed_url = urlparse(dss.base_url)
                ip_addr = socket.gethostbyname(parsed_url.hostname)

                if ipaddress.ip_address(ip_addr).is_private:
                    if self._allow_private_addresses:
                        check.skip()
                    else:
                        check.record_failed(
                            summary=f"DSS host {parsed_url.netloc} is not publicly addressable",
                            details=f"DSS (URL: {dss.base_url}, netloc: {parsed_url.netloc}, resolved IP: {ip_addr}) is not publicly addressable",
                        )

            with self.check("DSS instance is reachable", [dss.participant_id]) as check:
                try:
                    # dummy search query
                    _, q = dss.find_op_intent(extent=self._valid_search_area)
                    self.record_query(q)
                except QueryError as e:
                    self.record_queries(e.queries)
                    q = e.queries[0]
                    # status code 999 means we could not even get a valid HTTP reply,
                    # either from a time-out or an un-routable address, implying the DSS is likely unavailable.
                    # if the code is anything else than 999, we got an actual HTTP reply, and as far as this
                    # scenario is concerned, the DSS is available.
                    if q.status_code == 999:
                        check.record_failed(
                            summary=f"Could not reach DSS instance",
                            details=f"{q.response.get('content', '')}; {e}",
                            query_timestamps=[q.request.timestamp],
                        )
