from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstancesResource
from monitoring.uss_qualifier.scenarios.interuss.dss.pool_info import (
    PoolInfo as CommonPoolInfo,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class PoolInfo(CommonPoolInfo, TestScenario):
    def __init__(
        self,
        dss_instances: DSSInstancesResource,
    ):
        super().__init__(dss_instances.dss_instances)
