from typing import Optional, List

from implicitdict import ImplicitDict

from monitoring.monitorlib.dicts import JSONAddress
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.requirements.documentation import RequirementSetID
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


class TestedRolesConfiguration(ImplicitDict):
    report_path: str
    """Path of HTML file to contain a fulfilled-requirements-based view of the test report"""


class ReportHTMLConfiguration(ImplicitDict):
    html_path: str
    """Path of HTML file to contain an HTML rendering of the test report"""


class GraphConfiguration(ImplicitDict):
    gv_path: str
    """Path of GraphViz (.gv) text file to contain a visualization of the test run"""


class ReportConfiguration(ImplicitDict):
    report_path: str
    """File name of the report to write (if test_config provided) or read (if test_config not provided)"""

    redact_access_tokens: bool = True
    """When True, look for instances of "Authorization" keys in the report with values starting "Bearer " and redact the signature from those access tokens"""


class ArtifactsConfiguration(ImplicitDict):
    report: Optional[ReportConfiguration] = None
    """Configuration for report generation"""

    report_html: Optional[ReportHTMLConfiguration] = None
    """If specified, configuration describing how an HTML version of the report should be generated"""

    graph: Optional[GraphConfiguration] = None
    """If specified, configuration describing a desired graph visualization summarizing the test run"""

    tested_roles: Optional[TestedRolesConfiguration] = None
    """If specified, configuration describing a desired report summarizing tested requirements for each specified participant and role"""


class USSQualifierConfigurationV1(ImplicitDict):
    test_run: Optional[TestConfiguration] = None
    """If specified, configuration describing how to perform a test run"""

    artifacts: Optional[ArtifactsConfiguration] = None
    """If specified, configuration describing the artifacts related to the test run"""


class USSQualifierConfiguration(ImplicitDict):
    v1: Optional[USSQualifierConfigurationV1]
    """Configuration in version 1 format"""

    @staticmethod
    def from_string(config_string: str) -> "USSQualifierConfiguration":
        return ImplicitDict.parse(
            load_dict_with_references(config_string), USSQualifierConfiguration
        )
