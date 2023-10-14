# Contributing to this repository

Welcome to this repository and thank you for your interest in contributing to it.

Contributions should follow [the general InterUSS contributions process](https://github.com/interuss/tsc/blob/main/repo_contributions.md).  Additional information specific to this repository is provided below.

## Formatting and verification

This repository has a very strict Python linter, as well as very strict expected formats for a number of other artifacts such as Markdown files.  Correct formatting can be verified with `make lint` from the repository root.  But, in most cases manual formatting is not necessary to resolve issues -- instead, `make format` from the repository root should automatically reformat Python and most other mere-formatting issues without changing functionality.  Because `make lint` is part of the integration tests, `make format` should generally be run before integration tests.

## Integration tests

When [a PR is created](https://github.com/interuss/tsc/blob/main/repo_contributions.md#create-draft-pr-in-interuss-repository), the [continuous integration (CI) tests for this repository](./.github/workflows/CI.md) will run, and the PR will generally not be reviewed until they pass (unless [committer help is requested](https://github.com/interuss/tsc/blob/main/repo_contributions.md#request-committer-help-via-comment-in-pr) to address the failure).  See [the continuous integration test documentation](./.github/workflows/CI.md) for how to run these tests on your local system more quickly and efficiently to be confident your PR will pass the CI tests when created (or when updates are made).

### Failing "uss_qualifier tests" CI check

If `make presubmit` succeeds on a developer's local machine, the GitHub CI actions should succeed as well.  [A known issue](https://github.com/interuss/monitoring/issues/28) frequently causes the "uss_qualifier tests" check to fail.  If the failed check indicates a query response code of 999 (this is the code InterUSS indicates when no response is received), this is very likely the problem.  A committer can rerun the CI check and it is likely to succeed on the second try with no changes.

If anyone can resolve [issue #28](https://github.com/interuss/monitoring/issues/28) which causes this problem, that help would be enormously appreciated by InterUSS.

## uss_qualifier test scenarios

[uss_qualifier](monitoring/uss_qualifier/README.md) is InterUSS's automated testing framework.  To contribute new test scenarios or test scenario updates, the following process should generally be followed.

### Requirements

The purpose of uss_qualifier is to validate that a system under test meets a set of requirements.  A test scenario is simply a procedure to arrange situations where a system's compliance to requirements can be measured.  Before development of a test scenario can begin, the requirements it is intended to verify must be defined and identified.  uss_qualifier has [a specific, required way](monitoring/uss_qualifier/requirements/README.md) to document requirements in Markdown files.  In the case of requirements originating from copyrighted documents such as ASTM standards, the full content of the requirements should generally not be copied into these requirement definitions, but the existence of each requirement must be explicitly declared even if the explanatory content does not exist in this repository.

### Implementation plan

If the test to be implemented will require new functionality outside of uss_qualifier (e.g., in mock_uss or in automated_testing_interfaces), the test is likely a large contribution and should usually follow the portions of the [general contributing procedure](https://github.com/interuss/tsc/blob/main/repo_contributions.md#contributing-procedure) regarding creating an issue and/or discussing the approach.

When developing a test will involve multiple phases (e.g., test scenario X depends on resource Y which will follow automated test interface Z), the phases with no incomplete dependencies should generally be completed before the dependent phases are started (e.g., automated test interface Z should be completed before working on resource Y which should be completed before working on test scenario X).

Phases that can be completed or progressed in a single small PR that does not depend on concepts or tools that are not yet fully implemented do not require the pre-coordination described above.

### Scenario documentation

uss_qualifier test scenario documentation describes what is needed for the scenario ([resources](monitoring/uss_qualifier/resources/README.md)), what will happen in the scenario ([test cases, test steps](monitoring/uss_qualifier/scenarios/README.md#test-scenarios)), and what observations may result in concluding that a system under test fails to meet one or more requirements ([test checks](monitoring/uss_qualifier/scenarios/README.md#test-checks)).  Documented test checks are the only times uss_qualifier may indicate that a system under test has failed part or all of the test, and these checks should indicate which [requirements](#requirements) uss_qualifier can conclude that the system under test failed to meet when it fails that check.  Documentation for test checks that are not yet implemented in the test scenario Python code should include a `TODO: Implement` note (or similar).

If the test scenario will be implemented in a separate PR from the documentation (usually recommended), the PR containing test scenario documentation should also include an empty (the overridden `run` method contains just a `pass` statement) [test scenario implemented in Python](monitoring/uss_qualifier/scenarios/README.md#structure) -- this will ensure that the test scenario documentation format and content is validated by the CI.  See [the noop test scenario](monitoring/uss_qualifier/scenarios/dev/noop.py) for an example of a nearly-empty test scenario.

If the test scenario is long, note that the documentation does not need to be created all in one PR.  Small PRs are preferred, and it may make sense to write the documentation for one test case (per PR) at a time, for instance.

### Scenario implementation

Once all necessary prerequisites (e.g., resources) are available and the test scenario documentation is complete, actually writing the code of the test scenario should be fairly straightforward.  Before creating a PR, the test scenario code must at least have been successfully tested by the developer.  Ideally, a test configuration included in the CI (see list of configurations tested in [uss_qualifier's run_locally.sh](monitoring/uss_qualifier/run_locally.sh)) should run the test scenario.  If the test scenario is not run as part of the CI, the PR author must clearly indicate why they are sure the test scenario has been implemented correctly.
