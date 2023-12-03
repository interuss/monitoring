# Modify activated flight test step fragment

This page describes the content of a common test case where a valid user flight intent in activated state is tentatively
modified by a flight planned. Multiple outcomes may be valid.
See `modify_activated_flight_intent` in [test_steps.py](test_steps.py).

## Successful modification check

All flight intent data provided is correct and valid. The (already activated) provided flight intent may be in conflict
with another activated flight, but only if this conflict already existed before the modification was initiated.

If the provided flight intent is not in conflict with another intent the USS should have successfully modified the
flight per **[astm.f3548.v21.SCD0030](../../requirements/astm/f3548/v21.md)**.
If the USS fails to modify the flight, wrongly indicates a conflict, or wrongly indicates the activated state of the
flight, this check will fail.

If the provided flight intent is in conflict with another intent and that a pre-existing conflict was present, the USS
may have decided to be more conservative and to not support modification.
In such case, the USS may indicate that the operation is not supported instead of modifying the flight per **[astm.f3548.v21.SCD0030](../../requirements/astm/f3548/v21.md)**.
If the USS fails to modify the flight, or fails to indicate that the modification is not supported, or wrongly indicates
the activated state of the flight, this check will fail.

Do take note that if the USS rejects the modification when a pre-existing conflict was present, this check will not fail,
but the following *Rejected modification check* will. Refer to this check for more information.

## Rejected modification check

If the provided flight intent is in conflict with another intent and that a pre-existing conflict was present, the USS
may have rejected the modification instead of modifying it or indicating that the modification is not supported. This
could be the case for example if the USS does not support directly update of intents and instead delete the previous one
and create a new one. This may or may not be strictly speaking a failure to meet a requirement, but we cannot
distinguish between an actual failure to meet the requirement and a reasonable behavior due to implementation
limitations.

As such, if the pre-existing conflict was present, and that the USS rejected the modification, this check will fail with
a low severity per **[astm.f3548.v21.SCD0030](../../requirements/astm/f3548/v21.md)**. This won't actually fail the test
but will serve as a warning.

## Failure check

All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept the flight. If the USS indicates that the injection attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.
