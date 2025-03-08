# ASTM F3548 makeUssReport test scenario

## Overview
In this scenario, the report of previously executed ASTM F3548 UTM scenario(s) are examined to identify USSs' base URLs
so that the makeUssReport endpoint can be called for each of these base URLs.

## Resources

### utm_auth

uss_qualifier uses this authorization is in the test scenario to act as a USS and perform calls to makeUssReport.

## Call makeUssReport interface test case

### Identify USS base URLs test step

In this test step, the report of all test activities up to this point is examined to identify instances of the [Validation of operational intents test scenario](./flight_intent_validation/flight_intent_validation.md) in which the [Plan Valid Flight test step](./flight_intent_validation/flight_intent_validation.md#plan-valid-flight-test-step) is inspected to find the base URL of the tested_uss.

If no such executed scenarios are found, the remainder of this scenario will not be performed.

### Call makeUssReport interfaces test step

The makeUssReport endpoint is called for each of the USS base URLs identified in the previous step.

#### ⚠️ makeUssReport responds correctly check

If the USS's makeUssReport endpoint does not respond correctly, the USS will have failed to comply with **[astm.f3548.v21.USS0105,4](../../../requirements/astm/f3548/v21.md)**.
