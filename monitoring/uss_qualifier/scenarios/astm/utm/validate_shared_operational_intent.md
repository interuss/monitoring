# Validate flight sharing test step

This step verifies that a created flight is shared properly per ASTM F3548-21 by querying the DSS for flights in the area of the flight intent, and then retrieving the details from the USS if the operational intent reference is found.  See `OpIntentValidator.expect_shared()` in [test_steps.py](test_steps.py).

## DSS responses check

**astm.f3548.v21.DSS0005**

## Operational intent shared correctly check

If a reference to the operational intent for the flight is not found in the DSS, this check will fail per **astm.f3548.v21.USS0005** and **astm.f3548.v21.OPIN0025**.

## Operational intent details retrievable check

If the operational intent details for the flight cannot be retrieved from the USS, this check will fail per **astm.f3548.v21.USS0105** and **astm.f3548.v21.OPIN0025**.

## Operational intent details data format check

If the operational intent details response does not validate against [the GetOperationalIntentDetailsResponse schema of the OpenAPI specification](https://github.com/astm-utm/Protocol/blob/v1.0.0/utm.yaml#L1120), this check fill fail per **astm.f3548.v21.USS0105**.

## Correct operational intent details check

If the operational intent details reported by the USS do not match the user's flight intent, this check will fail per **interuss.automated_testing.flight_planning.ExpectedBehavior** and **astm.f3548.v21.OPIN0025**.

## Off-nominal volumes check

**astm.f3548.v21.OPIN0015**

## Vertices check

**astm.f3548.v21.OPIN0020**
