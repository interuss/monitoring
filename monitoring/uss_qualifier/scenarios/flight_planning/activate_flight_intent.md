# Activate flight test step

This page describes the content of a common test step where a valid user flight intent should be successfully activated by a flight planner.  See `activate_flight_intent` in [test_steps.py](test_steps.py).

## 🛑 Successful activation check

All flight intent data provided is correct and valid and free of conflict in space and time, therefore it should have been activated by the USS per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.  If the USS indicates a conflict, this check will fail.  If the USS indicates that the flight was rejected, this check will fail.  If the USS indicates that the injection attempt failed, this check will fail.

## 🛑 Failure check

All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept the flight. If the USS indicates that the injection attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.