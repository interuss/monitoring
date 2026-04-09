from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstancesResource
from monitoring.uss_qualifier.scenarios.astm.dss.pool_info import (
    PoolInfo as CommonPoolInfo,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class PoolInfo(TestScenario, CommonPoolInfo):
    def __init__(
        self,
        dss_instances: DSSInstancesResource,
    ):
        super().__init__()
