# Contributing to this repository

Welcome to this repository and thank you for your interest in contributing to it.

Contributions should follow [the general InterUSS contributions process](https://github.com/interuss/tsc/blob/main/repo_contributions.md).  Additional information specific to this repository is provided below.

## Issues requiring more information

When more information is needed from an issue's author to continue investigation/consideration of the issue, a maintainer may apply the `more-informationed-needed` label following a comment requesting the additional information.  [no-response](https://github.com/lee-dohm/no-response?tab=readme-ov-file#action-flow) will automatically close the issue if no additional information is provided.  New information (in the form of a comment on the issue) should remove the label and reopen the issue if it was closed.

## Formatting and verification

This repository has a very strict Python linter, as well as very strict expected formats for a number of other artifacts such as Markdown files.  Correct formatting can be verified with `make lint` from the repository root.  But, in most cases manual formatting is not necessary to resolve issues -- instead, `make format` from the repository root should automatically reformat Python and most other mere-formatting issues without changing functionality.  Because `make lint` is part of the integration tests, `make format` should generally be run before integration tests.

## Integration tests

When [a PR is created](https://github.com/interuss/tsc/blob/main/repo_contributions.md#create-draft-pr-in-interuss-repository), the [continuous integration (CI) tests for this repository](./.github/workflows/CI.md) will run, and the PR will generally not be reviewed until they pass (unless [committer help is requested](https://github.com/interuss/tsc/blob/main/repo_contributions.md#request-committer-help-via-comment-in-pr) to address the failure).  See [the continuous integration test documentation](./.github/workflows/CI.md) for how to run these tests on your local system more quickly and efficiently to be confident your PR will pass the CI tests when created (or when updates are made).

### Troubleshooting

See [the continuous integration test documentation](./.github/workflows/CI.md) for how to troubleshoot failing CI for a PR.

### Failing "uss_qualifier tests" CI check

If `make presubmit` succeeds on a developer's local machine, the GitHub CI actions should succeed as well.  If `make presubmit` succeeds locally but the GitHub CI actions fail, that may indicate help from an InterUSS committer would be helpful.

## uss_qualifier test scenarios

See [the specific contribution guidelines for test scenarios](./monitoring/uss_qualifier/scenarios/CONTRIBUTING.md) when creating or modify uss_qualifier test scenarios.
