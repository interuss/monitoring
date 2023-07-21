import json

from implicitdict import ImplicitDict

from monitoring.uss_qualifier.reports.report import TestSuiteReport
from monitoring.uss_qualifier.resources.resource import Resource


class TestSuiteReportResource(Resource[TestSuiteReport]):
    report: TestSuiteReport

    def __init__(
        self,
        specification: TestSuiteReport,
    ):
        self.report = ImplicitDict.parse(
            json.loads(json.dumps(specification)),
            TestSuiteReport,
        )
