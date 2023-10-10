from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss.isa_validation import (
    ISAValidation as CommonISAValidation,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class ISAValidation(TestScenario, CommonISAValidation):
    pass
