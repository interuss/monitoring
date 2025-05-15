import os
from typing import Dict, Iterable, List

import marko.block
import marko.element
import marko.inline
from marko.md_renderer import MarkdownRenderer

from monitoring.uss_qualifier.documentation import text_of
from monitoring.uss_qualifier.requirements.documentation import RequirementID
from monitoring.uss_qualifier.scenarios.documentation.definitions import (
    TestCaseDocumentation,
    TestCheckTree,
    TestStepDocumentation,
)
from monitoring.uss_qualifier.scenarios.documentation.parsing import (
    TEST_STEP_SUFFIX,
    get_documentation,
    get_documentation_filename,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def format_scenario_documentation(
    test_scenarios: Iterable[TestScenarioType],
) -> Dict[str, str]:
    """Get new documentation content after autoformatting Scenario docs.

    Returns:
        Mapping from .md filename to content that file should contain (which is
        different from what it currently contains).
    """
    new_versions: Dict[str, str] = {}
    to_check = []
    for test_scenario in test_scenarios:
        doc_filename = get_documentation_filename(test_scenario)
        if not os.path.exists(doc_filename):
            continue
        to_check.append(doc_filename)

    checked = set()
    while to_check:
        # Pick the next documentation file to check
        doc_filename = to_check.pop(0)
        if doc_filename in checked:
            continue
        checked.add(doc_filename)

        # Load the .md file if it exists
        with open(doc_filename, "r") as f:
            original = f.read()
        md = marko.Markdown(renderer=MarkdownRenderer)
        doc = md.parse(original)
        original = md.render(doc)

        linked_test_steps = _enumerate_linked_test_steps(doc, doc_filename)
        to_check.extend(linked_test_steps)

        _add_requirement_links(doc, doc_filename)

        # Return the formatted version
        formatted = md.render(doc)
        if formatted != original:
            new_versions[doc_filename] = formatted
    return new_versions


def _add_requirement_links(parent: marko.element.Element, doc_path: str) -> None:
    if hasattr(parent, "children") and not isinstance(parent.children, str):
        for i, child in enumerate(parent.children):
            if isinstance(child, str):
                continue
            if isinstance(child, marko.inline.StrongEmphasis):
                if not child.children:
                    raise ValueError(
                        "No content found in bolded (**strong emphasis**) section of documentation"
                    )
                if len(child.children) != 1:
                    content_types = ", ".join(
                        c.__class__.__name__ for c in child.children
                    )
                    raise ValueError(
                        f"Expected exactly 1 content element in bolded (**strong emphasis**) section of documentation, but instead found {len(child.children)} content elements ({content_types})"
                    )
                if isinstance(child.children[0], marko.inline.Link):
                    # Requirement already has link; ensure validity
                    req_id = RequirementID(text_of(child.children[0]))
                    if not os.path.exists(req_id.md_file_path()):
                        raise ValueError(
                            f'Requirement ID "{req_id}" implies that {req_id.md_file_path()} should exist, but it does not exist'
                        )
                    href = child.children[0].dest
                    doc_dir = os.path.dirname(doc_path)
                    linked_path = os.path.normpath(os.path.join(doc_dir, href))
                    if linked_path != req_id.md_file_path():
                        href = os.path.relpath(req_id.md_file_path(), doc_dir)
                        child.children[0].dest = href

                elif isinstance(child.children[0], marko.inline.RawText):
                    # Replace plaintext with link to requirement definition
                    req_id = RequirementID(text_of(child.children[0]))
                    if not os.path.exists(req_id.md_file_path()):
                        raise ValueError(
                            f'Requirement ID "{req_id}" implies that {req_id.md_file_path()} should exist, but it does not exist'
                        )
                    href = os.path.relpath(
                        req_id.md_file_path(), os.path.dirname(doc_path)
                    )
                    del child.children[0]
                    link = marko.parse(f"[{req_id}]({href})").children[0].children[0]
                    child.children.append(link)
                else:
                    raise ValueError(
                        f"Found a {child.children[0].__class__.__name__} content element in a bolded (**strong emphasis**) section of documentation, but expected either a Link or RawText"
                    )
            else:
                _add_requirement_links(child, doc_path)


def _enumerate_linked_test_steps(
    parent: marko.element.Element, doc_path: str
) -> List[str]:
    linked_test_steps = []
    if hasattr(parent, "children") and not isinstance(parent.children, str):
        for i, child in enumerate(parent.children):
            if isinstance(child, str):
                continue
            elif (
                isinstance(child, marko.block.Heading)
                and text_of(child).lower().endswith(TEST_STEP_SUFFIX)
                and child.children
                and isinstance(child.children[0], marko.block.inline.Link)
            ):
                href = child.children[0].dest
                doc_dir = os.path.dirname(doc_path)
                linked_path = os.path.normpath(os.path.join(doc_dir, href))
                linked_test_steps.append(linked_path)
            else:
                linked_test_steps.extend(_enumerate_linked_test_steps(child, doc_path))
    return linked_test_steps


def update_checks_without_severity(test_scenarios: List[TestScenarioType]) -> None:
    checks_without_severity = TestCheckTree(scenarios={})
    for test_scenario in test_scenarios:
        docs = get_documentation(test_scenario)

        for case in docs.cases:
            for step in case.steps:
                for check in step.checks:
                    if "severity" not in check or check.severity is None:
                        checks_without_severity.add_check(
                            scenario=test_scenario, case=case, step=step, check=check
                        )
        if "cleanup" in docs:
            for check in docs.cleanup.checks:
                if "severity" not in check or check.severity is None:
                    checks_without_severity.add_check(
                        scenario=test_scenario,
                        case=TestCaseDocumentation(name="Cleanup", steps=[]),
                        step=docs.cleanup,
                        check=check,
                    )
    preexisting_checks_without_severity = TestCheckTree.preexisting(
        "checks_without_severity.json"
    )
    new_checks_without_severity = checks_without_severity.without(
        preexisting_checks_without_severity
    )
    removed_checks_without_severity = preexisting_checks_without_severity.without(
        checks_without_severity
    )
    if new_checks_without_severity.n == 0 and removed_checks_without_severity.n > 0:
        print(
            f"Updated tracking to note removal of {removed_checks_without_severity.n} checks without documented severity."
        )
        checks_without_severity.write("checks_without_severity.json")
    elif new_checks_without_severity.n > 0:
        print(
            f"WARNING: There are {new_checks_without_severity.n} new checks without documented severity:\n{new_checks_without_severity.render()}"
        )
    else:
        print(
            f"Number of checks without documented severity ({preexisting_checks_without_severity.n}) has not changed."
        )
