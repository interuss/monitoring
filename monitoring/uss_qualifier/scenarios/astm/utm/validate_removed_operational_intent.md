# Validate operational intent removed test step fragment

This step verifies that ending/removal/cancellation of a flight resulted in the operational intent reference being removed from the DSS.
It does so by querying the DSS for operational intents in the area of the flight before and after an attempted removal.
This assumes an area lock on the extent of the flight intent.

See `OpIntentValidator.expect_removed()` in [test_steps.py](test_steps.py).

## 🛑 DSS responses check

**[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**

## 🛑 Operational intent not shared check
If the operational intent reference for the flight is still found in the area of the flight intent, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../requirements/interuss/automated_testing/flight_planning.md)**.
