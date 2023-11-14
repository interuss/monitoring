from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss.token_validation import (
    TokenValidation as CommonTokenValidation,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class TokenValidation(TestScenario, CommonTokenValidation):
    pass
