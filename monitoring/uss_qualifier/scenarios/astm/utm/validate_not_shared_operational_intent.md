# Validate operational intent not shared test step fragment

This step verifies that a previous attempt to create a flight did not result in a flight being shared with the DSS.
It does so by querying the DSS for operational intents in the area of the flight before and after an attempted creation.
This assumes an area lock on the extent of the flight intent.

See `OpIntentValidator.expect_not_shared()` in [test_steps.py](test_steps.py).

## 🛑 DSS responses check

**[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**

## 🛑 Operational intent not shared check
If there are new operational intent references in the area of the flight intent, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../requirements/interuss/automated_testing/flight_planning.md)**.
