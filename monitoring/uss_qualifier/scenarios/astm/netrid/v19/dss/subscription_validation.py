from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss.subscription_validation import (
    SubscriptionValidation as CommonSubscriptionValidation,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class SubscriptionValidation(TestScenario, CommonSubscriptionValidation):
    pass
