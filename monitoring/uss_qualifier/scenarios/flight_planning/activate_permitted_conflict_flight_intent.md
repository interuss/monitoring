# Activate flight with permitted equal priority conflict test step fragment

This page describes the content of a common test step where a user flight intent should be successfully activated by a
flight planner, given that there exists a permitted conflict with an equal priority flight intent.
See `activate_permitted_conflict_flight_intent` in [prioritization_test_steps.py](prioritization_test_steps.py).

Do note that this step does not check if the USS correctly sends a notification to the USS responsible for the
conflicting flight intent.

## Successful activation check

If the USS fails to activate the flight or otherwise wrongly indicates a conflict, this check will fail, per
**[astm.f3548.v21.SCD0065](../../requirements/astm/f3548/v21.md)**.

## Failure check

All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept the flight. If the USS indicates that the injection attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.
