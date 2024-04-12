import argparse
import os
import sys

from implicitdict import ImplicitDict
from monitoring.monitorlib.inspection import import_submodules
from monitoring.uss_qualifier import scenarios, suites, action_generators
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.suites.definitions import TestSuiteDefinition
from monitoring.uss_qualifier.suites.documentation.documentation import (
    find_test_suites,
    make_test_suite_documentation,
)


def main(lint: bool) -> int:
    import_submodules(scenarios)
    import_submodules(suites)
    import_submodules(action_generators)

    test_suite_docs = {}
    for suite_yaml_file in find_test_suites():
        suite_def: TestSuiteDefinition = ImplicitDict.parse(
            load_dict_with_references("file://" + suite_yaml_file), TestSuiteDefinition
        )
        suite_doc_file = os.path.splitext(suite_yaml_file)[0] + ".md"
        new_docs = make_test_suite_documentation(
            suite_def, suite_yaml_file, suite_doc_file
        )
        for k, v in new_docs.items():
            test_suite_docs[k] = v

    changes = False
    for suite_doc_file, suite_doc_content in test_suite_docs.items():
        if os.path.exists(suite_doc_file):
            with open(suite_doc_file, "r") as f:
                existing_content = f.read()
            if existing_content == suite_doc_content:
                # No changes needed
                continue
        changes = True
        if lint:
            print(
                f"Test suite documentation must be regenerated with `make format`: {suite_doc_file}"
            )
        else:
            with open(suite_doc_file, "w") as f:
                f.write(suite_doc_content)
            print(f"Wrote test suite documentation: {suite_doc_file}")

    if lint and changes:
        return -1
    if not changes:
        print("No test suite documentation changes needed.")
    return os.EX_OK


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automatically manage test suite documentation"
    )

    parser.add_argument(
        "--lint",
        action="store_true",
        help="When specified, do not make any documentation changes and exit with error if changes are needed.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(main(args.lint))
