from typing import Optional, List, Union, Iterable

from implicitdict import StringBasedDateTime
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.reports.report import TestRunReport, TestSuiteActionReport
from monitoring.uss_qualifier.reports.tested_requirements.data_types import (
    TestRunInformation,
    TestedBreakdown,
    ParticipantVerificationStatus,
    FAIL_CLASS,
    NOT_TESTED_CLASS,
    PASS_CLASS,
)
from monitoring.uss_qualifier.signatures import compute_signature


def compute_test_run_information(report: TestRunReport) -> TestRunInformation:
    def print_datetime(t: Optional[StringBasedDateTime]) -> Optional[str]:
        if t is None:
            return None
        return t.datetime.strftime("%Y-%m-%d %H:%M:%S %Z")

    return TestRunInformation(
        test_run_id=compute_signature(report),
        start_time=print_datetime(report.report.start_time),
        end_time=print_datetime(report.report.end_time),
        baseline=report.baseline_signature,
        environment=report.environment_signature,
    )


def compute_overall_status(
    participant_breakdown: TestedBreakdown,
) -> ParticipantVerificationStatus:
    overall_status = ParticipantVerificationStatus.Pass
    for package in participant_breakdown.packages:
        for req in package.requirements:
            if req.classname == FAIL_CLASS:
                return ParticipantVerificationStatus.Fail
            elif req.classname == NOT_TESTED_CLASS:
                overall_status = ParticipantVerificationStatus.Incomplete
            elif req.classname == PASS_CLASS:
                pass
            else:
                return ParticipantVerificationStatus.Unknown
    return overall_status


def find_participant_system_versions(
    report: TestSuiteActionReport,
    participant_ids: Union[ParticipantID, Iterable[ParticipantID]],
) -> List[str]:
    if isinstance(participant_ids, ParticipantID):
        participant_ids = [participant_ids]
    test_suite, test_scenario, action_generator = report.get_applicable_report()
    result = []
    if test_suite:
        for action in report.test_suite.actions:
            result.extend(find_participant_system_versions(action, participant_ids))
    elif action_generator:
        for action in report.action_generator.actions:
            result.extend(find_participant_system_versions(action, participant_ids))
    elif test_scenario:
        if (
            report.test_scenario.scenario_type
            in (
                "scenarios.versioning.get_system_versions.GetSystemVersions",
                "scenarios.versioning.GetSystemVersions",
            )
            and "notes" in report.test_scenario
        ):
            for participant_id in participant_ids:
                if participant_id in report.test_scenario.notes:
                    system_identity, version = report.test_scenario.notes[
                        participant_id
                    ].message.split("=")
                    result.append(version)
    return result


def get_system_version(system_versions: List[str]) -> Optional[str]:
    if not system_versions:
        return None
    elif len(system_versions) > 1 and any(
        v != system_versions[0] for v in system_versions
    ):
        return "CONFLICTED: " + " and ".join(system_versions)
    else:
        return system_versions[0]
