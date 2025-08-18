import arrow

from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.scenarios.scenario import (
    ScenarioCannotContinueError,
    ScenarioPhase,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestRunCannotContinueError as _TestRunCannotContinueError,
)

from .utils import (
    HideLogOutput,
    assert_date_is_close_to_now,
    build_testable_pending_check,
)


def test_no_result_mean_passed():
    """Test that when using the PendingCheck's context and not recording result, a 'pass' is recorded"""

    pc, report = build_testable_pending_check()

    assert not report.passed_checks
    assert not report.failed_checks

    with pc:
        pass

    assert report.passed_checks
    assert not report.failed_checks


def test_skip():
    """Test the PendingCheck's skip function, ensuring nothing is recorded"""

    pc, report = build_testable_pending_check()

    assert not report.passed_checks
    assert not report.failed_checks

    with pc:
        pc.skip()

    assert not report.passed_checks
    assert not report.failed_checks


def test_report_passed():
    """Test the PendingCheck's record_passed function, with expected results in the TestReport"""

    pc, report = build_testable_pending_check()

    assert not report.passed_checks
    assert not report.failed_checks

    with pc:
        pc.record_passed()

    assert report.passed_checks
    assert not report.failed_checks

    result = report.passed_checks[0]

    assert result.name == "test-doc-name"
    assert result.participants == ["test-participant"]
    assert result.requirements == ["test.req"]
    assert_date_is_close_to_now(result.timestamp.datetime)


def test_report_failed():
    """Test the PendingCheck's record_failed function, with expected results in the TestReport"""

    pc, report = build_testable_pending_check(severity=Severity.Medium)

    assert not report.passed_checks
    assert not report.failed_checks

    with pc:
        pc.record_failed(
            summary="test-summary",
            details="test-details",
            query_timestamps=["2025-02-18 12:34:56"],
            additional_data={"test-additional": "test-data"},
        )

    assert not report.passed_checks
    assert report.failed_checks

    result = report.failed_checks[0]

    assert result.name == "test-doc-name"
    assert result.participants == ["test-participant"]
    assert result.requirements == ["test.req"]
    assert_date_is_close_to_now(result.timestamp.datetime)
    assert result.summary == "test-summary"
    assert result.details == "test-details"
    assert result.severity == Severity.Medium
    assert "test-additional" in result.additional_data
    assert result.additional_data["test-additional"] == "test-data"
    assert result.query_report_timestamps
    assert result.query_report_timestamps[0].datetime == arrow.get(
        "2025-02-18 12:34:56"
    )


def test_report_failed_severities_no_severity():
    """Test the PendingCheck's record_failed function behavior with severities, where a severity must be define in the documentation. This function test the case where no severity is defined."""

    pc, _ = build_testable_pending_check()

    with pc:
        try:
            pc.record_failed(summary="")
            assert False  # ValueError should have been raised, no error defined
        except ValueError:
            pass


def test_report_failed_severities_severity_in_documentation():
    """Test the PendingCheck's record_failed function behavior with severities, where a severity must be define in the documentation. This function test the case where severity is defined in the documentation."""

    pc, report = build_testable_pending_check(severity=Severity.Low)

    with pc:
        pc.record_failed(summary="")

    assert report.failed_checks
    assert report.failed_checks[0].severity == Severity.Low


def test_report_failed_stopfast_non_low():
    """Test the PendingCheck's record_failed function behavior with stop_fast parameter, with non-low severities that should stop the test"""

    for severity in [Severity.Medium, Severity.High, Severity.Critical]:
        pc, report = build_testable_pending_check(severity=severity, stop_fast=True)

        with pc:
            try:
                with HideLogOutput():
                    pc.record_failed(summary="")
                assert False  # TestRunCannotContinueError should have been raised
            except _TestRunCannotContinueError:
                assert report.failed_checks
                assert (
                    report.failed_checks[0].severity == Severity.Critical
                )  # Severity is escalated to Critical


def test_report_failed_stopfast_low():
    """Test the PendingCheck's record_failed function behavior with stop_fast parameter, with low severity that shouldn't stop the test"""

    pc, report = build_testable_pending_check(severity=Severity.Low, stop_fast=True)

    with pc:
        pc.record_failed(summary="")
        assert report.failed_checks
        assert report.failed_checks[0].severity == Severity.Low


def test_report_failed_stopfast_outside_cleanup():
    """Test the PendingCheck's record_failed function behavior with stop_fast parameter, with errors outside the cleanup phase that should stop the test"""

    for phase in [
        ScenarioPhase.Undefined,
        ScenarioPhase.NotStarted,
        ScenarioPhase.ReadyForTestCase,
        ScenarioPhase.ReadyForTestStep,
        ScenarioPhase.ReadyForCleanup,
        ScenarioPhase.Complete,
    ]:
        pc, report = build_testable_pending_check(
            severity=Severity.Medium, phase=phase, stop_fast=True
        )

        with pc:
            try:
                with HideLogOutput():
                    pc.record_failed(summary="")
                assert False  # TestRunCannotContinueError should have been raised
            except _TestRunCannotContinueError:
                assert report.failed_checks
                assert (
                    report.failed_checks[0].severity == Severity.Critical
                )  # Severity is escalated to Critical


def test_report_failed_stopfast_during_cleanup():
    """Test the PendingCheck's record_failed function behavior with stop_fast parameter, with errors during the cleanup phase that shouldn't stop the test"""

    pc, report = build_testable_pending_check(
        severity=Severity.Medium, phase=ScenarioPhase.CleaningUp, stop_fast=True
    )

    with pc:
        pc.record_failed(summary="")
        assert report.failed_checks
        assert report.failed_checks[0].severity == Severity.Medium


def test_report_failed_exceptions_critical():
    """Test the PendingCheck's record_failed function behavior with critical severity that should raise an exception"""

    pc, report = build_testable_pending_check(severity=Severity.Critical)

    with pc:
        try:
            pc.record_failed(summary="")
            assert False  # TestRunCannotContinueError should have been raised
        except _TestRunCannotContinueError:
            assert report.failed_checks
            assert report.failed_checks[0].severity == Severity.Critical


def test_report_failed_exceptions_high():
    """Test the PendingCheck's record_failed function behavior with high severity that should raise an exception"""

    pc, report = build_testable_pending_check(severity=Severity.High)

    with pc:
        try:
            pc.record_failed(summary="")
            assert False  # TestRunCannotContinueError should have been raised
        except ScenarioCannotContinueError:
            assert report.failed_checks
            assert report.failed_checks[0].severity == Severity.High


def test_report_failed_no_exceptions():
    """Test the PendingCheck's record_failed function behavior with medium and low severities that shouldn't raise an exception"""

    for severity in [Severity.Medium, Severity.Low]:
        pc, report = build_testable_pending_check(severity=severity)

        with pc:
            pc.record_failed(summary="")
            assert report.failed_checks
            assert report.failed_checks[0].severity == severity


def test_on_failed_check_passing():
    """Test the PendingCheck's on_failed_check hook, that should only be called when test fails. This test test successful/skipped tests"""

    def dontcallme():
        assert False  # This function shouldn't have been called

    pc, _ = build_testable_pending_check(on_failed_check=dontcallme)

    with pc:
        pass  # NB: Assertion is done in dontcallme

    with pc:
        pc.record_passed()  # NB: Assertion is done in dontcallme

    with pc:
        pc.skip()  # NB: Assertion is done in dontcallme


def test_on_failed_check_failling():
    """Test the PendingCheck's on_failed_check hook, that should only be called when test fails. This test test failed tests"""

    has_been_called_with_check_result = None

    def callme(check):
        nonlocal has_been_called_with_check_result
        has_been_called_with_check_result = check

    pc, report = build_testable_pending_check(
        on_failed_check=callme, severity=Severity.Medium
    )

    with pc:
        pc.record_failed(summary="")
    assert has_been_called_with_check_result
    assert has_been_called_with_check_result == report.failed_checks[0]
