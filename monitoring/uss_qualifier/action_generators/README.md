# Action generators

The bulk of uss_qualifier's automated testing logic is contained in [test scenarios](../scenarios/README.md).  A [test suite](../suites/README.md) is essentially a static "playlist" of test actions to perform (test scenarios, action generators, and other test suites), all of which ultimately resolve to test scenarios.  An action generator is essentially a dynamic "playlist" of test actions -- it can generate test actions that vary according to provided resource values, situations, or other conditions only necessarily known at runtime.

For documentation purposes, all action generators must statically declare the test actions they may take.  However, whether each (or any) of these actions will actually be taken at runtime cannot be statically determined in general.

## Parallel execution in action generators

An action generator's `actions()` method yields one of:

- a `TestSuiteAction` — executed sequentially, as before.
- a `list[list[TestSuiteAction]]` — a *parallel group*. The outer list holds the branches to execute concurrently; each inner list is a sequence of actions executed in order within its own branch.

Example:

```python
def actions(self) -> Iterator[TestSuiteAction | list[list[TestSuiteAction]]]:
    yield base_action                               # sequential
    yield [[A1, A2, A3], [B1, B2, B3]]              # A and B in parallel
```

When a parallel group is yielded, each branch runs on its own thread. Reports are appended to the parent report in branch order.

### Constraints

Each branch shares the same `Resource` instances unless the action generator hands out distinct ones. If a resource has mutable state that two branches would race on, the generator must produce isolated copies - typically by declaring `ResourceModifier`-based variants and calling `.adjust(index)` for each branch.

If a branch fails with `on_failure: Abort` (or hits a critical problem), the other branches are signalled to stop at the next action boundary. In-progress actions still finish.
