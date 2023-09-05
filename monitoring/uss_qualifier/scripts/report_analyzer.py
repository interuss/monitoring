import sys
import json

from implicitdict import ImplicitDict

from monitoring.uss_qualifier.reports.report import (
    TestRunReport,
    TestSuiteReport,
    TestScenarioReport,
)


def parse_report(path: str) -> TestRunReport:
    with open(path, "r") as f:
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
            print("   has #queries: ", len(step.queries)) if step.get(
                "queries"
            ) is not None else print("   has #queries: 0")
            for q in step.queries if step.get("queries") is not None else []:
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

    for a in r.report.test_suite.actions:
        print("Types of actions (test_suite, test_scenario, action_generator): ")
        print(a._get_applicable_report())

    suite_reports = {
        r.test_suite.name: r.test_suite
        for r in r.report.test_suite.actions
        if r.get("test_suite") is not None
    }
    scenario_reports = {
        r.test_scenario.name: r.test_scenario
        for r in r.report.test_suite.actions
        if r.get("test_scenario") is not None
    }

    print("Available suite reports: ", suite_reports.keys())
    print("Available scenario reports: ", scenario_reports.keys())

    if len(sys.argv) > 2:
        look_at_scenario(scenario_reports[sys.argv[2]])
        return 0


if __name__ == "__main__":
    sys.exit(main())
