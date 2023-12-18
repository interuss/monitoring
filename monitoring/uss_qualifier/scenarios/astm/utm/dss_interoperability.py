import ipaddress
import socket
from typing import List
from urllib.parse import urlparse

from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3548.v21.api import Volume4D, Volume3D, Polygon, LatLngPoint

from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstancesResource,
    DSSInstanceResource,
    DSSInstance,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario

VERTICES: List[LatLngPoint] = [
    LatLngPoint(lng=130.6205, lat=-23.6558),
    LatLngPoint(lng=130.6301, lat=-23.6898),
    LatLngPoint(lng=130.6700, lat=-23.6709),
    LatLngPoint(lng=130.6466, lat=-23.6407),
]
SHORT_WAIT_SEC = 5


class DSSInteroperability(TestScenario):
    _dss_primary: DSSInstance
    _dss_others: List[DSSInstance]

    def __init__(
        self,
        primary_dss_instance: DSSInstanceResource,
        all_dss_instances: DSSInstancesResource,
    ):
        super().__init__()
        self._dss_primary = primary_dss_instance.dss
        self._dss_others = [
            dss
            for dss in all_dss_instances.dss_instances
            if not dss.is_same_as(primary_dss_instance.dss)
        ]

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

                if dss.has_private_address:
                    self.record_note(
                        f"{dss.participant_id}_private_address",
                        f"DSS instance (URL: {dss.base_url}, netloc: {parsed_url.netloc}, resolved IP: {ip_addr}) is declared as explicitly having a private address, skipping check",
                    )
                elif ipaddress.ip_address(ip_addr).is_private:
                    check.record_failed(
                        summary=f"DSS host {parsed_url.netloc} is not publicly addressable",
                        details=f"DSS (URL: {dss.base_url}, netloc: {parsed_url.netloc}, resolved IP: {ip_addr}) is not publicly addressable",
                    )

            with self.check("DSS instance is reachable", [dss.participant_id]) as check:
                # dummy search query
                dss.find_op_intent(
                    extent=Volume4D(
                        volume=Volume3D(outline_polygon=Polygon(vertices=VERTICES))
                    )
                )
