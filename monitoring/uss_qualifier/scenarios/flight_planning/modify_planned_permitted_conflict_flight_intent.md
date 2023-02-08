# Modify planned flight with permitted equal priority conflict test step

This page describes the content of a common test step where a user flight intent should be successfully modified by a
flight planner, given that there exists a permitted conflict with an equal priority flight intent.
See `modify_planned_permitted_conflict_flight_intent` in [prioritization_test_steps.py](prioritization_test_steps.py).

Do note that this step does not check if the USS correctly sends a notification to the USS responsible for the
conflicting flight intent.

## Successful modification check

If the USS fails to modify the flight or otherwise wrongly indicates a conflict, this check will fail, per
**[astm.f3548.v21.SCD0060](../../requirements/astm/f3548/v21.md)**.
