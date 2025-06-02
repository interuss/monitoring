from monitoring.uss_qualifier.scenarios.astm.dss.datastore_access import (
    DatastoreAccess as CommonDatastoreAccess,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class DatastoreAccess(TestScenario, CommonDatastoreAccess):
    pass
