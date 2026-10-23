# Contributing to uss_qualifier test scenarios

[uss_qualifier](../README.md) is InterUSS's automated testing framework.  This document describes how to create new uss_qualifier scenarios and modify existing scenarios.  Please see [repository-wide contribution guidance](../../../CONTRIBUTING.md) before proceeding to the rest of this document.

## Creating a new test scenario

### Requirements

The purpose of uss_qualifier is to validate that a system under test meets a set of requirements.  A test scenario is simply a procedure to arrange situations where a system's compliance to requirements can be measured.  Before development of a test scenario can begin, the requirements it is intended to verify must be defined and identified.  uss_qualifier has [a specific, required way](../requirements/README.md) to document requirements in Markdown files.  In the case of requirements originating from copyrighted documents such as ASTM standards, the full content of the requirements should generally not be copied into these requirement definitions, but the existence of each requirement must be explicitly declared even if the explanatory content does not exist in this repository.

### Implementation plan

If the test to be implemented will require new functionality outside of uss_qualifier (e.g., in mock_uss or in automated_testing_interfaces), the test is likely a large contribution and should usually follow the portions of the [general contributing procedure](https://github.com/interuss/tsc/blob/main/repo_contributions.md#contributing-procedure) regarding creating an issue and/or discussing the approach.

When developing a test will involve multiple phases (e.g., test scenario X depends on resource Y which will follow automated test interface Z), the phases with no incomplete dependencies should generally be completed before the dependent phases are started (e.g., automated test interface Z should be completed before working on resource Y which should be completed before working on test scenario X).

Phases that can be completed or progressed in a single small PR that does not depend on concepts or tools that are not yet fully implemented do not require the pre-coordination described above.

### Scenario documentation

uss_qualifier test scenario documentation describes what is needed for the scenario ([resources](../resources/README.md)), what will happen in the scenario ([test cases, test steps](./README.md#test-scenarios)), and what observations may result in concluding that a system under test fails to meet one or more requirements ([test checks](./README.md#test-checks)).  Documented test checks are the only times uss_qualifier may indicate that a system under test has failed part or all of the test, and these checks should indicate which [requirements](#requirements) uss_qualifier can conclude that the system under test failed to meet when it fails that check.  Documentation for test checks that are not yet implemented in the test scenario Python code should include a `TODO: Implement` note (or similar).

If the test scenario will be implemented in a separate PR from the documentation (this is usually recommended), the PR containing test scenario documentation should also include an empty (the overridden `run` method contains just a `pass` statement) [test scenario implemented in Python](./README.md#structure) -- this will ensure that the test scenario documentation format and content is validated by the CI.  See [the noop test scenario](./dev/noop.py) for an example of a nearly-empty test scenario.

If the test scenario is long, note that the documentation does not need to be created all in one PR.  Small PRs are preferred, and it may make sense to write the documentation for one test case (per PR) at a time, for instance.

### Scenario implementation

Once all necessary prerequisites (e.g., resources) are available and the test scenario documentation is complete, actually writing the code of the test scenario should be fairly straightforward.  Before creating a PR, the test scenario code must at least have been successfully tested by the developer.  Ideally, a test configuration included in the CI (see list of configurations tested in [uss_qualifier's run_locally.sh](../run_locally.sh)) should run the test scenario.  If the test scenario is not run as part of the CI, the PR author must clearly indicate why they are sure the test scenario has been implemented correctly.

See more information about test scenarios and their implementation in [test scenario documentation](./README.md).

## Scenario best practices

### Check severities

[Test documentation](./README.md#documentation) requires checks to be [annotated with the severity of a failure of that check](./README.md#test-checks).  In general, the severity chosen should be the lowest level that is still correct.

If one or more requirements were violated, but it is possible for the test scenario to continue (the check doesn't indicate that necessary preparation for a later portion of the test scenario failed), choose Medium severity rather than High severity.

Only choose High severity if the test scenario cannot continue due to the outcome being checked (for instance, a resource necessary later in the scenario was not emplaced successfully).

If a failing check does not indicate violation of a requirement, strongly consider simply removing that check from the test scenario.  If the outcome of the check is sufficiently important despite not indicating that any requirements were violated, then annotate it as Low severity.

Critical severity is reserved for a catastrophic failure that indicates the entire test run cannot continue.  This severity should be extraordinarily rare in test scenario documentation as test scenarios should be self-contained/encapsulated and not affect other later test scenarios (under the appropriate assumptions).

### Fake URLs

In some tests, fake URLs must be provided (for instance, the base URL when creating an operational intent reference in a DSS instance when the details for that operational intent reference will not actually be served by any USS).  In all cases when such fake URLs are provided, they should use the value obtained (or would be obtained) from `make_fake_url` in [monitorlib/testing.py](../../monitorlib/testing.py).  If the fake URL is specified in a data file rather than a Python file, it should follow the format of `https://testdummy.interuss.org/interuss` followed by the path of the file (minus extension) relative to the repository root; e.g., `https://testdummy.interuss.org/interuss/monitoring/uss_qualifier/configurations/dev/f3548_self_contained` if the URL was defined in [uss_qualifier/configurations/dev/f3548_self_contained.yaml](../configurations/dev/f3548_self_contained.yaml).  One or more suffix paths can be appended if multiple different fake URLs are needed in the same originating file; e.g., `https://testdummy.interuss.org/interuss/monitoring/uss_qualifier/configurations/dev/f3548_self_contained/planning_area/original`

This convention allows a user to more easily determine where a stray resource/link (e.g., operational intent reference) originated if/when it is encountered outside its intended test.
