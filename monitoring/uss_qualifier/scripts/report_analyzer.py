import json
import sys

from implicitdict import ImplicitDict

from monitoring.uss_qualifier.reports.report import (
    TestRunReport,
    TestScenarioReport,
    TestSuiteReport,
)


def parse_report(path: str) -> TestRunReport:
    with open(path) as f:
        report = json.load(f)
        return ImplicitDict.parse(report, TestRunReport)


def look_at_test_suite(ts: TestSuiteReport):
    print("test-suite: " + ts.name)


def look_at_scenario(ts: TestScenarioReport):
    print("Looking at test scenario: ", ts.name)
    print("Has #cases: ", len(ts.cases))
    for tcr in ts.cases:
        print("  Test case report: ", tcr.name)
        print("  has #steps: ", len(tcr.steps))
        for step in tcr.steps:
            print("   step: ", step.name)
            (
                print("   has #queries: ", len(step.queries or []))
                if step.get("queries") is not None
                else print("   has #queries: 0")
            )
            for q in step.get("queries", []):
                print(f"    {q.response.elapsed_s} - {q.request.url}")


def main():
    """
    Print some infos about a report's content.

    Usage: python report_analyzer.py <path-to-report.json> <test_scenario_name>
    Eg: python report_analyzer.py output/report_netrid_v22a.json "ASTM NetRID nominal behavior"
    """
    if len(sys.argv) < 2:
        print(
            "Usage: python report_analyzer.py <path-to-report.json> <test_scenario_name>"
        )
        return 1

    r = parse_report(sys.argv[1])

    if r.report.test_suite is None:
        print("No test_suite in report")
        return 0

    for a in r.report.test_suite.actions:
        print("Types of actions (test_suite, test_scenario, action_generator): ")
        print(a._get_applicable_report())

    suite_reports = {
        subr.test_suite.name: subr.test_suite
        for subr in r.report.test_suite.actions
        if "test_suite" in subr and subr.test_suite is not None
    }
    scenario_reports = {
        subr.test_scenario.name: subr.test_scenario
        for subr in r.report.test_suite.actions
        if "test_scenario" in subr and subr.test_scenario is not None
    }

    print("Available suite reports: ", suite_reports.keys())
    print("Available scenario reports: ", scenario_reports.keys())

    if len(sys.argv) > 2:
        look_at_scenario(scenario_reports[sys.argv[2]])
        return 0


if __name__ == "__main__":
    sys.exit(main())
