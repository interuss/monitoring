# Plan flight with non-permitted equal priority conflict test step fragment

This page describes the content of a common test step where a user flight intent should be denied planning because of
a non-permitted conflict with an equal priority flight intent.
See `plan_conflict_flight_intent` in [prioritization_test_steps.py](prioritization_test_steps.py).

## 🛑 Incorrectly planned check

If the USS successfully plans the flight or otherwise fails to indicate a conflict, it means they failed to detect the
conflict with the pre-existing flight.
Therefore, this check will fail if the USS indicates success in creating the flight from the user flight intent,
per **[astm.f3548.v21.SCD0035](../../requirements/astm/f3548/v21.md)**.

## 🛑 Failure check

All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept the flight. If the USS indicates that the injection attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.
