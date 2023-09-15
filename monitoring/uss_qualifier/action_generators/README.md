# Action generators

The bulk of uss_qualifier's automated testing logic is contained in [test scenarios](../scenarios/README.md).  A [test suite](../suites/README.md) is essentially a static "playlist" of test actions to perform (test scenarios, action generators, and other test suites), all of which ultimately resolve to test scenarios.  An action generator is essentially a dynamic "playlist" of test actions -- it can generate test actions that vary according to provided resource values, situations, or other conditions only necessarily known at runtime.

For documentation purposes, all action generators must statically declare the test actions they may take.  However, whether each (or any) of these actions will actually be taken at runtime cannot be statically determined in general.
