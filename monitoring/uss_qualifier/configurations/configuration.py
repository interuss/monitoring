from typing import Optional, List, Dict

from implicitdict import ImplicitDict

from monitoring.monitorlib.dicts import JSONAddress
from monitoring.uss_qualifier.reports.validation.definitions import (
    ValidationConfiguration,
)
from monitoring.uss_qualifier.requirements.definitions import RequirementCollection
from monitoring.uss_qualifier.resources.definitions import ResourceCollection
from monitoring.uss_qualifier.suites.definitions import (
    TestSuiteActionDeclaration,
)

ParticipantID = str
"""String that refers to a participant being qualified by uss_qualifier"""


class TestConfiguration(ImplicitDict):
    action: TestSuiteActionDeclaration
    """The action this test configuration wants to run (usually a test suite)"""

    non_baseline_inputs: Optional[List[JSONAddress]] = None
    """List of portions of the configuration that should not be considered when computing the test baseline signature (e.g., environmental definitions)."""

    resources: ResourceCollection
    """Declarations for resources used by the test suite"""


TestedRequirementsCollectionIdentifier = str
"""Identifier for a requirements collection, local to a TestedRequirementsConfiguration artifact configuration."""


class TestedRequirementsConfiguration(ImplicitDict):
    report_name: str
    """Name of subfolder in output path to contain the rendered templated report"""

    requirement_collections: Optional[
        Dict[TestedRequirementsCollectionIdentifier, RequirementCollection]
    ]
    """Definition of requirement collections specific to production of this artifact."""

    participant_requirements: Optional[
        Dict[ParticipantID, TestedRequirementsCollectionIdentifier]
    ]
    """If a requirement collection is specified for a participant, only the requirements in the specified collection will be listed on that participant's report."""


class SequenceViewConfiguration(ImplicitDict):
    redact_access_tokens: bool = True
    """When True, look for instances of "Authorization" keys in the report with values starting "Bearer " and redact the signature from those access tokens"""


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


class ArtifactsConfiguration(ImplicitDict):
    output_path: str
    """Path to folder where artifacts should be written."""

    raw_report: Optional[RawReportConfiguration] = None
    """Configuration for raw report generation"""

    report_html: Optional[ReportHTMLConfiguration] = None
    """If specified, configuration describing how an HTML version of the raw report should be generated"""

    templated_reports: Optional[List[TemplatedReportConfiguration]] = None
    """List of report templates to be rendered"""

    tested_requirements: Optional[List[TestedRequirementsConfiguration]] = None
    """If specified, list of configurations describing desired reports summarizing tested requirements for each participant"""

    sequence_view: Optional[SequenceViewConfiguration] = None
    """If specified, configuration describing a desired report describing the sequence of events that occurred during the test"""


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
