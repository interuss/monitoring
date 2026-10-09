# Validate operational intent removed test step fragment

This step verifies that ending/removal/cancellation of a flight resulted in the operational intent reference being removed from the DSS, and that the USS no longer provides the details of that operational intent.
It does so by querying the DSS for operational intents in the area of the flight before and after an attempted removal, and then querying the USS for the details of the removed operational intent.
This assumes an area lock on the extent of the flight intent.

See `OpIntentValidator.expect_removed()` in [test_steps.py](test_steps.py).

## 🛑 DSS responses check

**[astm.f3548.v21.DSS0005,2](../../../requirements/astm/f3548/v21.md)**

## 🛑 Operational intent not shared check
If the operational intent reference for the flight is still found in the area of the flight intent, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../requirements/interuss/automated_testing/flight_planning.md)**.

## ⚠️ Removed operational intent details not found check
The USS no longer manages the removed operational intent, so when queried for its details, it must respond with
[the 404 response defined by the OpenAPI specification](https://github.com/astm-utm/Protocol/blob/v1.0.0/utm.yaml#L3513-L3518).
If it responds with any other status code, it fails to properly implement the OpenAPI specification that is part of
**[astm.f3548.v21.USS0105,1](../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Not found response has the proper error message body check
If the 404 response above does not have a body that is a valid `ErrorResponse`, the USS fails to properly implement
the OpenAPI specification that is part of **[astm.f3548.v21.USS0105,1](../../../requirements/astm/f3548/v21.md)**.
