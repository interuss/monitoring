from monitoring.uss_qualifier.scenarios.astm.dss.crdb_access import (
    CRDBAccess as CommonCRDBAccess,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class CRDBAccess(TestScenario, CommonCRDBAccess):
    pass
