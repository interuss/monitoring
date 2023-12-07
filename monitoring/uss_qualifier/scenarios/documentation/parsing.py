import inspect
import os
from typing import List, Dict, Type, Any, Optional

import marko
import marko.element
import marko.inline

from monitoring import uss_qualifier as uss_qualifier_module
from monitoring.monitorlib.inspection import fullname, get_module_object_by_name
from monitoring.monitorlib.versioning import repo_url_of
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.documentation import text_of
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName
from monitoring.uss_qualifier.scenarios.documentation.definitions import (
    TestStepDocumentation,
    TestCheckDocumentation,
    TestCaseDocumentation,
    TestScenarioDocumentation,
)

RESOURCES_HEADING = "resources"
CLEANUP_HEADING = "cleanup"
TEST_SCENARIO_SUFFIX = " test scenario"
TEST_CASE_SUFFIX = " test case"
TEST_STEP_SUFFIX = " test step"
TEST_STEP_FRAGMENT_SUFFIX = " test step fragment"
TEST_CHECK_SUFFIX = " check"


_test_step_cache: Dict[str, TestStepDocumentation] = {}


def _length_of_section(values, start_of_section: int) -> int:
    level = values[start_of_section].level
    c = start_of_section + 1
    while c < len(values):
        if isinstance(values[c], marko.block.Heading) and values[c].level == level:
            break
        c += 1
    return c - start_of_section - 1


def _parse_test_check(
    values, doc_filename: str, anchors: Dict[Any, str]
) -> TestCheckDocumentation:
    name = text_of(values[0])[0 : -len(TEST_CHECK_SUFFIX)]
    url = repo_url_of(doc_filename + anchors[values[0]])
    has_todo = False

    reqs: List[str] = []
    c = 1
    while c < len(values):
        if isinstance(values[c], marko.block.Paragraph):
            if "TODO:" in text_of(values[c]):
                has_todo = True
            for child in values[c].children:
                if isinstance(child, marko.inline.StrongEmphasis):
                    reqs.append(RequirementID(text_of(child)))
        c += 1

    severity = None
    for s in Severity:
        if name.startswith(s.symbol):
            severity = s
            name = name[len(s.symbol) :].lstrip()
            break

    return TestCheckDocumentation(
        name=name,
        url=url,
        applicable_requirements=reqs,
        has_todo=has_todo,
        severity=severity,
    )


def _get_linked_test_step_fragment(
    doc_filename: str, origin_filename: str
) -> TestStepDocumentation:
    absolute_path = os.path.abspath(
        os.path.join(os.path.dirname(origin_filename), doc_filename)
    )
    if absolute_path not in _test_step_cache:
        if not os.path.exists(absolute_path):
            raise ValueError(
                f'Test step fragment document "{doc_filename}" linked from "{origin_filename}" does not exist at "{absolute_path}"'
            )
        with open(absolute_path, "r") as f:
            doc = marko.parse(f.read())

        if (
            not isinstance(doc.children[0], marko.block.Heading)
            or doc.children[0].level != 1
            or not text_of(doc.children[0]).lower().endswith(TEST_STEP_FRAGMENT_SUFFIX)
        ):
            raise ValueError(
                f'The first line of "{absolute_path}" must be a level-1 heading with the name of the test step fragment + "{TEST_STEP_FRAGMENT_SUFFIX}" (e.g., "# Successful flight injection{TEST_STEP_FRAGMENT_SUFFIX}")'
            )

        anchors = _get_anchors(doc)
        values = doc.children
        dc = _length_of_section(values, 0)
        _test_step_cache[absolute_path] = _parse_test_step(
            values[0 : dc + 1], absolute_path, anchors
        )
    return _test_step_cache[absolute_path]


def _parse_test_step(
    values, doc_filename: str, anchors: Dict[Any, str]
) -> TestStepDocumentation:
    name = text_of(values[0])
    if name.lower().endswith(TEST_STEP_SUFFIX):
        name = name[0 : -len(TEST_STEP_SUFFIX)]
    url = repo_url_of(doc_filename + anchors[values[0]])

    checks: List[TestCheckDocumentation] = []
    if values[0].children and isinstance(
        values[0].children[0], marko.block.inline.Link
    ):
        # We include the content of the linked test step fragment document before
        # extracting content from this section.
        linked_step_fragment = _get_linked_test_step_fragment(
            values[0].children[0].dest, doc_filename
        )
        url = linked_step_fragment.url
        checks = linked_step_fragment.checks.copy()

    c = 1
    while c < len(values):
        if isinstance(values[c], marko.block.Heading):
            if text_of(values[c]).lower().endswith(TEST_CHECK_SUFFIX):
                # Start of a test step section
                dc = _length_of_section(values, c)
                check = _parse_test_check(values[c : c + dc + 1], doc_filename, anchors)
                checks.append(check)
                c += dc
            elif isinstance(values[c].children[0], marko.block.inline.Link):
                # Heading is a link, so we infer this is a linked test step fragment
                dc = _length_of_section(values, c)
                linked_step_fragment = _get_linked_test_step_fragment(
                    values[c].children[0].dest, doc_filename
                )
                url = linked_step_fragment.url
                checks.extend(linked_step_fragment.checks.copy())
                c += dc
            else:
                c += 1
        else:
            c += 1
    return TestStepDocumentation(name=name, url=url, checks=checks)


def _parse_test_case(
    values, doc_filename: str, anchors: Dict[Any, str]
) -> TestCaseDocumentation:
    name = text_of(values[0])[0 : -len(TEST_CASE_SUFFIX)]

    url = repo_url_of(doc_filename + anchors[values[0]])

    steps: List[TestStepDocumentation] = []
    c = 1
    while c < len(values):
        if isinstance(values[c], marko.block.Heading):
            if text_of(values[c]).lower().endswith(TEST_STEP_SUFFIX):
                # Start of a test step section
                dc = _length_of_section(values, c)
                step = _parse_test_step(values[c : c + dc + 1], doc_filename, anchors)
                steps.append(step)
                c += dc
            else:
                c += 1
        else:
            c += 1

    return TestCaseDocumentation(name=name, steps=steps, url=url)


def _parse_resources(values) -> List[str]:
    resource_level = values[0].level + 1
    resources: List[str] = []
    c = 1
    while c < len(values):
        if (
            isinstance(values[c], marko.block.Heading)
            and values[c].level == resource_level
        ):
            # This is a resource
            resources.append(text_of(values[c]))
        c += 1
    return resources


def get_documentation_filename(scenario: Type) -> str:
    return os.path.splitext(inspect.getfile(scenario))[0] + ".md"


def _get_anchors(
    value, header_counts: Optional[Dict[str, int]] = None
) -> Dict[Any, str]:
    if header_counts is None:
        header_counts = {}
    anchors = {}

    if isinstance(value, marko.block.Heading):
        heading_text = text_of(value)
        for s in Severity:
            if heading_text.startswith(s.symbol):
                heading_text = heading_text[len(s.symbol) :].lstrip()
                break
        base_anchor = "#" + heading_text.lower().replace(" ", "-")
        if base_anchor not in header_counts:
            anchors[value] = base_anchor
        else:
            anchors[value] = f"{base_anchor}-{header_counts[base_anchor]}"
        header_counts[base_anchor] = header_counts.get(base_anchor, 0) + 1

    if hasattr(value, "children"):
        for child in value.children:
            subanchors = _get_anchors(child, header_counts)
            for k, v in subanchors.items():
                anchors[k] = v

    return anchors


def _parse_documentation(scenario: Type) -> TestScenarioDocumentation:
    # Load the .md file matching the Python file where this scenario type is defined
    doc_filename = get_documentation_filename(scenario)
    if not os.path.exists(doc_filename):
        raise ValueError(
            "Test scenario `{}` does not have the required documentation file `{}`".format(
                fullname(scenario), doc_filename
            )
        )
    with open(doc_filename, "r") as f:
        doc = marko.parse(f.read())
    url = repo_url_of(doc_filename)
    anchors = _get_anchors(doc)

    # Extract the scenario name from the first top-level header
    if (
        not isinstance(doc.children[0], marko.block.Heading)
        or doc.children[0].level != 1
        or not text_of(doc.children[0]).lower().endswith(TEST_SCENARIO_SUFFIX)
    ):
        raise ValueError(
            'The first line of {} must be a level-1 heading with the name of the scenario + "{}" (e.g., "# ASTM NetRID nominal behavior{}")'.format(
                doc_filename, TEST_SCENARIO_SUFFIX, TEST_SCENARIO_SUFFIX
            )
        )
    scenario_name = text_of(doc.children[0])[0 : -len(TEST_SCENARIO_SUFFIX)]

    # Step through the document to extract important structured components
    test_cases: List[TestCaseDocumentation] = []
    resources = None
    cleanup = None
    c = 1
    while c < len(doc.children):
        if not isinstance(doc.children[c], marko.block.Heading):
            c += 1
            continue

        header_text = text_of(doc.children[c])

        if header_text.lower().strip() == RESOURCES_HEADING:
            # Start of the Resources section
            if resources is not None:
                raise ValueError(
                    f'Only one major section may be titled "{RESOURCES_HEADING}"'
                )
            dc = _length_of_section(doc.children, c)
            resources = _parse_resources(doc.children[c : c + dc + 1])
            c += dc
        elif header_text.lower().strip() == CLEANUP_HEADING:
            # Start of the Cleanup section
            if cleanup is not None:
                raise ValueError(
                    'Only one major section may be titled "{CLEANUP_HEADING}"'
                )
            dc = _length_of_section(doc.children, c)
            cleanup = _parse_test_step(
                doc.children[c : c + dc + 1], doc_filename, anchors
            )
            c += dc
        elif header_text.lower().endswith(TEST_CASE_SUFFIX):
            # Start of a test case section
            dc = _length_of_section(doc.children, c)
            test_case = _parse_test_case(
                doc.children[c : c + dc + 1], doc_filename, anchors
            )
            test_cases.append(test_case)
            c += dc
        else:
            c += 1

    kwargs = {
        "name": scenario_name,
        "cases": test_cases,
        "resources": resources,
        "url": url,
        "local_path": os.path.abspath(doc_filename),
    }
    if cleanup is not None:
        kwargs["cleanup"] = cleanup
    return TestScenarioDocumentation(**kwargs)


def get_documentation(scenario: Type) -> TestScenarioDocumentation:
    DOC_CACHE_ATTRIBUTE = f"_md_documentation_{scenario.__name__}"
    if not hasattr(scenario, DOC_CACHE_ATTRIBUTE):
        setattr(scenario, DOC_CACHE_ATTRIBUTE, _parse_documentation(scenario))
    return getattr(scenario, DOC_CACHE_ATTRIBUTE)


def get_documentation_by_name(
    scenario_type_name: TestScenarioTypeName,
) -> TestScenarioDocumentation:
    scenario_type = get_module_object_by_name(uss_qualifier_module, scenario_type_name)
    return get_documentation(scenario_type)
