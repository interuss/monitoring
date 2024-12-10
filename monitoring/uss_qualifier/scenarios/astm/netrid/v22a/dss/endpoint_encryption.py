from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss.endpoint_encryption import (
    EndpointEncryption as CommonEndpointEncryption,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class EndpointEncryption(TestScenario, CommonEndpointEncryption):
    pass
