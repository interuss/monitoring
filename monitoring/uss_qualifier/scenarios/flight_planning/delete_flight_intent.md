# Delete flight test step fragment

This page describes the content of a common test case where a flight intent should be successfully deleted by a flight planner.
See `delete_flight_intent` in [test_steps.py](test_steps.py).

## Successful deletion check

The flight ID provided is correct and corresponds to an existing flight intent, therefore it should have been deleted by
the USS per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.
If the USS indicates a failure, this check will fail.
