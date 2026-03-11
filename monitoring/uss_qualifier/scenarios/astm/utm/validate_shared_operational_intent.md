# Validate flight sharing test step fragment

This step verifies that a created flight is shared properly per ASTM F3548-21 by querying the DSS for flights in the area of the flight intent, and then retrieving the details from the USS if the operational intent reference is found.  See `OpIntentValidator.expect_shared()` in [test_steps.py](test_steps.py).

## 🛑 DSS responses check

If the DSS fails to properly respond to a valid search query for operational intents in an area,
it is in violation of **[astm.f3548.v21.DSS0005,2](../../../requirements/astm/f3548/v21.md)**, and this check will fail.

## 🛑 Operational intent shared correctly check

If a reference to the operational intent for the flight is not found in the DSS, this check will fail per **[astm.f3548.v21.USS0005](../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.OPIN0025](../../../requirements/astm/f3548/v21.md)**.

## 🛑 Operational intent for active flight not deleted check

If an activated operational intent is expected to exist after it has been modified or activated and that it is not found
in the DSS, this means that there is an active flight without a corresponding operational intent, then this check will
fail per **[interuss.automated_testing.flight_planning.FlightCoveredByOperationalIntent](../../../requirements/interuss/automated_testing/flight_planning.md)**.

## 🛑 Operational intent state is correct check

If the state of the operational intent found in the DSS does not match the user's flight intent, this check will fail per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../requirements/interuss/automated_testing/flight_planning.md)**.

## 🛑 Operational intent details retrievable check

If the operational intent details for the flight cannot be retrieved from the USS, this check will fail per **[astm.f3548.v21.USS0105,1](../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.OPIN0025](../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Operational intent details data format check

If the operational intent details response does not validate against [the GetOperationalIntentDetailsResponse schema of the OpenAPI specification](https://github.com/astm-utm/Protocol/blob/v1.0.0/utm.yaml#L1120), this check fill fail per **[astm.f3548.v21.USS0105,1](../../../requirements/astm/f3548/v21.md)**.

## 🛑 Operational intent reference reported by USS matches the one published to the DSS check

If any of the values in the operational intent reference reported by the USS do not match those values in the operational intent reference published to (and known by) the DSS, save for the OVN, this check will fail per  **[astm.f3548.v21.USS0005](../../../requirements/astm/f3548/v21.md)** since the values reported by the USS were not made discoverable via the DSS.

## 🛑 Operational intent details have not changed without publishing a new version to the DSS check

If the operational intent details exposed by the USS have changed without the USS having updated the operational intent reference in the DSS, this check will fail per:
- **[astm.f3548.v21.USS0105,1](../../../requirements/astm/f3548/v21.md)**  because the USS did not implement the operation _getOperationalIntentDetails_ correctly; and
- **[astm.f3548.v21.USS0005](../../../requirements/astm/f3548/v21.md)** because the USS did not make the operational intent correctly discoverable by the DSS.

Out of clarity, this check specifically targets cases where the USS changes details of the operational intent (volumes or priority) without a version or OVN change.

## 🛑 Correct operational intent details check

If the operational intent details reported by the USS do not match the user's flight intent, this check will fail per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../requirements/interuss/automated_testing/flight_planning.md)** and **[astm.f3548.v21.OPIN0025](../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Off-nominal volumes check

**[astm.f3548.v21.OPIN0015](../../../requirements/astm/f3548/v21.md)** specifies that nominal operational intents (Accepted and Activated) must not include any off-nominal 4D volumes, so this check will fail if an Accepted or Activated operational intent includes off-nominal volumes.

## ⚠️ Vertices check

**[astm.f3548.v21.OPIN0020](../../../requirements/astm/f3548/v21.md)**

## 🛑 Operational intent telemetry retrievable check

If:
- the operational intent is in an off-nominal state,
- that its telemetry cannot be retrieved from the USS, and
- that the USS does not explicitly indicate that no telemetry is available,

this check will fail per **[astm.f3548.v21.USS0105,2](../../../requirements/astm/f3548/v21.md)**.
