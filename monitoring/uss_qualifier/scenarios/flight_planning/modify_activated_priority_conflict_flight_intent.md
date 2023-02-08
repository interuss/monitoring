# Modify activated flight with higher priority conflict test step

This page describes the content of a common test step where a user flight intent should be denied modification because
of a conflict with a higher priority flight intent.
See `modify_activated_priority_conflict_flight_intent` in [prioritization_test_steps.py](prioritization_test_steps.py).

## Incorrectly modified check

If the USS successfully modifies the flight or otherwise fails to indicate a conflict, it means they failed to detect
the conflict with the pre-existing flight.
Therefore, this check will fail if the USS indicates success in modifying the flight from the user flight intent,
per **[astm.f3548.v21.SCD0030](../../requirements/astm/f3548/v21.md)**.
