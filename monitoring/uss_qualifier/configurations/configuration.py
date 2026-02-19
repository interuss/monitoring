from __future__ import annotations

from implicitdict import ImplicitDict, Optional

from monitoring.monitorlib.dicts import JSONAddress
from monitoring.uss_qualifier.action_generators.definitions import GeneratorTypeName
from monitoring.uss_qualifier.reports.validation.definitions import (
    ValidationConfiguration,
)
from monitoring.uss_qualifier.requirements.definitions import RequirementCollection
from monitoring.uss_qualifier.resources.definitions import ResourceCollection
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName
from monitoring.uss_qualifier.suites.definitions import (
    TestSuiteActionDeclaration,
    TestSuiteTypeName,
)

ParticipantID = str
"""String that refers to a participant being qualified by uss_qualifier"""


class InstanceIndexRange(ImplicitDict):
    lo: Optional[int]
    """If specified, no indices lower than this value will be included in the range."""

    i: Optional[int]
    """If specified, no index other than this one will be included in the range."""

    hi: Optional[int]
    """If specified, no indices higher than this value will be included in the range."""

    def includes(self, i: int) -> bool:
        if "i" in self and self.i is not None and i != self.i:
            return False
        if "lo" in self and self.lo is not None and i < self.lo:
            return False
        if "hi" in self and self.hi is not None and i > self.hi:
            return False
        return True


class ActionGeneratorSelectionCondition(ImplicitDict):
    """By default, select all action generators.  When specified, limit selection to specified conditions."""

    types: Optional[list[GeneratorTypeName]]
    """Only select action generators of the specified types."""


class TestSuiteSelectionCondition(ImplicitDict):
    """By default, select all test suites.  When specified, limit selection to specified conditions."""

    types: Optional[list[TestSuiteTypeName]]
    """Only select test suites of the specified types."""


class TestScenarioSelectionCondition(ImplicitDict):
    """By default, select all test scenarios.  When specified, limit selection to specified conditions."""

    types: Optional[list[TestScenarioTypeName]]
    """Only select test scenarios of the specified types."""


class NthInstanceCondition(ImplicitDict):
    """Select an action once a certain number of matching instances have happened."""

    n: list[InstanceIndexRange]
    """Only select an action if it is one of these nth instances."""

    where_action: TestSuiteActionSelectionCondition
    """Condition that an action must meet to be selected as an instance in this condition."""


class AncestorSelectionCondition(ImplicitDict):
    """Select ancestor actions meeting all the specified conditions."""

    of_generation: Optional[int]
    """The ancestor is exactly this many generations removed (1 = parent, 2 = grandparent, etc).

    If not specified, an ancestor of any generation meeting the `which` conditions will be selected."""

    which: list[TestSuiteActionSelectionCondition]
    """Only select an ancestor meeting ALL of these conditions."""


class TestSuiteActionSelectionCondition(ImplicitDict):
    """Condition for selecting TestSuiteActions.

    If more than one subcondition is specified, satisfaction of ALL subconditions are necessary to select the action.
    """

    is_action_generator: Optional[ActionGeneratorSelectionCondition]
    """Select these action generator actions."""

    is_test_suite: Optional[TestSuiteSelectionCondition]
    """Select these test suite actions."""

    is_test_scenario: Optional[TestScenarioSelectionCondition]
    """Select these test scenario actions."""

    regex_matches_name: Optional[str]
    """Select actions where this regular expression has a match in the action's name."""

    defined_at: Optional[list[JSONAddress]]
    """Select actions defined at one of the specified addresses.

    The top-level action in a test run is 'test_scenario', 'test_suite', or 'action_generator'.  Children use the
    'actions' property, but then must specify the type of the action.  So, e.g., the test scenario that is the third
    action of a test suite which is the second action in an action generator would be
    'action_generator.actions[1].test_suite.actions[2].test_scenario'.  An address that starts or ends with 'actions[i]'
    is invalid and will never match."""

    nth_instance: Optional[NthInstanceCondition]
    """Select only certain instances of matching actions."""

    has_ancestor: Optional[AncestorSelectionCondition]
    """Select only actions with a matching ancestor."""

    except_when: Optional[list[TestSuiteActionSelectionCondition]]
    """Do not select actions selected by any of these conditions, even when they are selected by one or more conditions above."""


class ExecutionConfiguration(ImplicitDict):
    include_action_when: Optional[list[TestSuiteActionSelectionCondition]] = None
    """If specified, only execute test actions if they are selected by ANY of these conditions (and not selected by any of the `skip_when` conditions)."""

    skip_action_when: Optional[list[TestSuiteActionSelectionCondition]] = None
    """If specified, do not execute test actions if they are selected by ANY of these conditions."""

    stop_fast: Optional[bool] = False
    """If true, escalate the Severity of any failed check to Critical in order to end the test run early."""

    stop_when_resource_not_created: Optional[bool] = False
    """If true, stop test execution if one of the resources cannot be created.  Otherwise, resources that cannot be created due to missing prerequisites are simply treated as omitted."""

    scenarios_filter: str | None
    """Filter test scenarios by scenario type using a regex. If the filter regex does not match within the scenario type, the scenario is skipped. When empty, all scenarios are executed. Useful for targeted debugging. Overridden by --filter"""


class TestConfiguration(ImplicitDict):
    action: TestSuiteActionDeclaration
    """The action this test configuration wants to run (usually a test suite)"""

    non_baseline_inputs: Optional[list[JSONAddress]] = None
    """List of portions of the configuration that should not be considered when computing the test baseline signature (e.g., environmental definitions)."""

    resources: ResourceCollection
    """Declarations for resources used by the test suite"""

    execution: Optional[ExecutionConfiguration]
    """Specification for how to execute the test run."""


TestedRequirementsCollectionIdentifier = str
"""Identifier for a requirements collection, local to a TestedRequirementsConfiguration artifact configuration.

This value will be displayed as RC-<VALUE> in the artifact.  To avoid confusion, no spaces are recommended in values of
this type; e.g., 'SCD_with_DSS' rather than 'SCD with DSS' or 'ServerProviderAndDisplayProvider' versus 'Service Provider
and Display Provider'.  Succinct names are recommended over lengthy ones."""


class TestedRequirementsConfiguration(ImplicitDict):
    report_name: str
    """Name of subfolder in output path to contain the rendered templated report"""

    requirement_collections: Optional[
        dict[TestedRequirementsCollectionIdentifier, RequirementCollection]
    ]
    """Definition of requirement collections specific to production of this artifact."""

    aggregate_participants: Optional[dict[ParticipantID, list[ParticipantID]]]
    """If specified, a list of 'aggregate participants', each of which is composed of multiple test participants.

    If specified, these aggregate participants are the preferred subject for `participant_requirements`.
    """

    participant_requirements: Optional[
        dict[ParticipantID, TestedRequirementsCollectionIdentifier | None]
    ]
    """If a requirement collection is specified for a participant, only the requirements in the specified collection will be listed on that participant's report.

    If a requirement collection is specified as None/null for a participant, all potentially-testable requirements will be included.

    If a participant is not listed, no report will be generated for them.
    """


class SequenceViewConfiguration(ImplicitDict):
    redact_access_tokens: bool = True
    """When True, look for instances of "Authorization" keys in the report with values starting "Bearer " and redact the signature from those access tokens"""

    render_kml: bool = True
    """When True, visualize geographic data for each scenario as a KML file."""


class ReportHTMLConfiguration(ImplicitDict):
    redact_access_tokens: bool = True
    """When True, look for instances of "Authorization" keys in the report with values starting "Bearer " and redact the signature from those access tokens"""


class TemplatedReportInjectedConfiguration(ImplicitDict):
    pass


class TemplatedReportConfiguration(ImplicitDict):
    template_url: str
    """Url of the template to download from"""

    report_name: str
    """Name of HTML file (without extension) to contain the rendered templated report"""

    configuration: Optional[TemplatedReportInjectedConfiguration] = None
    """Configuration to be injected in the templated report"""


class RawReportConfiguration(ImplicitDict):
    redact_access_tokens: bool = True
    """When True, look for instances of "Authorization" keys in the report with values starting "Bearer " and redact the signature from those access tokens"""

    indent: Optional[int] = None
    """To pretty-print JSON content, specify an indent level (generally 2), or omit or set to None to write compactly."""


class GloballyExpandedReportConfiguration(ImplicitDict):
    redact_access_tokens: bool = True
    """When True, look for instances of "Authorization" keys in the report with values starting "Bearer " and redact the signature from those access tokens"""


class TimingReportConfiguration(ImplicitDict):
    percentage_of_time_to_break_down: float = 100.0
    """Percentage of test time to break down in the timing report (smaller contributions are not reported)"""


class ArtifactsConfiguration(ImplicitDict):
    raw_report: Optional[RawReportConfiguration] = None
    """Configuration for raw report generation"""

    report_html: Optional[ReportHTMLConfiguration] = None
    """If specified, configuration describing how an HTML version of the raw report should be generated"""

    templated_reports: Optional[list[TemplatedReportConfiguration]] = None
    """List of report templates to be rendered"""

    tested_requirements: Optional[list[TestedRequirementsConfiguration]] = None
    """If specified, list of configurations describing desired reports summarizing tested requirements for each participant"""

    sequence_view: Optional[SequenceViewConfiguration] = None
    """If specified, configuration describing a desired report describing the sequence of events that occurred during the test"""

    globally_expanded_report: Optional[GloballyExpandedReportConfiguration] = None
    """If specified, configuration describing a desired report mimicking what might be seen had the test run been conducted manually."""

    timing_report: Optional[TimingReportConfiguration] = None
    """If specified, configuration describing a desired report describing where and how time was spent during the test."""


class USSQualifierConfigurationV1(ImplicitDict):
    test_run: Optional[TestConfiguration] = None
    """If specified, configuration describing how to perform a test run"""

    artifacts: Optional[ArtifactsConfiguration] = None
    """If specified, configuration describing the artifacts related to the test run"""

    validation: Optional[ValidationConfiguration] = None
    """If specified, configuration describing how to validate the output report (and return an error code if validation fails)"""


class USSQualifierConfiguration(ImplicitDict):
    v1: Optional[USSQualifierConfigurationV1]
    """Configuration in version 1 format"""
