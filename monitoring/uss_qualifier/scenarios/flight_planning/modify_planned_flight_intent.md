# Modify planned flight test step fragment

This page describes the content of a common test case where a valid user flight intent in planned state should be
successfully modified by a flight planner.  See `modify_planned_flight_intent` in [test_steps.py](test_steps.py).

## Successful modification check

All flight intent data provided is correct and valid and free of conflict in space and time, therefore it should have
been modified by the USS per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.
If the USS fails to modify the flight, wrongly indicates a conflict, or wrongly indicates the planned state of the
flight, this check will fail.

## Failure check

All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept the flight. If the USS indicates that the injection attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.
