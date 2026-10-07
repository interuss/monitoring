# ASTM SCD USS: Interfaces authentication test scenario

## Overview

Ensures that a USS rejects improperly-authenticated requests to the strategic coordination endpoints required by **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**, and **[astm.f3548.v21.USS0105,4](../../../../requirements/astm/f3548/v21.md)**.

## Resources

### tested_uss

[`FlightPlannerResource`](../../../../resources/flight_planning/flight_planners.py) for the USS under test.

### utm_auth

[`AuthAdapterResource`](../../../../resources/communications/auth_adapter.py) used to obtain credentials when acting as a USS to call the endpoints of the USS under test.

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) used to find the operational intent reference created by the USS under test, which provides the USS base URL.

### flight_intents

[`FlightIntentsResource`](../../../../resources/flight_planning/flight_intents_resource.py) providing `flight_1`, a nominal flight planned by the USS under test so that its base URL can be discovered.

## Setup test case

This test case sets up the rest of the scenario by collecting the USS base URL for the USS under test.

### Successfully plan flight test step

uss_qualifier instructs the USS under test to plan a flight, queries the DSS for the resulting operational intent reference, and records the USS base URL from that reference for use in the rest of this scenario.

#### [Plan successfully](../../../flight_planning/plan_flight_intent.md)

#### [Validate operational intent is shared](../validate_shared_operational_intent.md)

## Endpoint authorization test case

This test case ensures that the USS properly authenticates requests to its strategic coordination endpoints.

### Get operational intent details authentication test step

uss_qualifier queries the USS under test's getOperationalIntentDetails endpoint for an arbitrary operational intent ID using several kinds of credentials, both permitted and not permitted by [the OpenAPI specification](https://github.com/astm-utm/Protocol/blob/v1.0.0/utm.yaml#L3471-L3473).

#### ⚠️ Get operational intent details with missing credentials check

If the USS under test allows the fetching of operational intent details without any credentials being presented, it is in violation of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Get operational intent details with invalid credentials check

If the USS under test allows the fetching of operational intent details with credentials that are well-formed but invalid, it is in violation of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Get operational intent details with an incorrect scope check

If the USS under test allows the fetching of operational intent details with valid credentials but an incorrect scope, it is in violation of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Unauthorized requests return the proper error message body check

If, for any of the rejected requests above, the USS under test does not return a proper error message body, it fails to properly implement the OpenAPI specification that is part of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Get operational intent details with valid credentials check

If the USS under test rejects a request to fetch operational intent details with a 401 or 403 when valid credentials with an appropriate scope are presented, it is in violation of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**.

### Notify operational intent details changed authentication test step

uss_qualifier sends the USS under test's notifyOperationalIntentDetailsChanged endpoint a notification that an arbitrary operational intent was removed, using several kinds of credentials, both permitted and not permitted by [the OpenAPI specification](https://github.com/astm-utm/Protocol/blob/v1.0.0/utm.yaml#L3610-L3612).

#### ⚠️ Notify operational intent details changed with missing credentials check

If the USS under test accepts an operational intent details change notification without any credentials being presented, it is in violation of **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Notify operational intent details changed with invalid credentials check

If the USS under test accepts an operational intent details change notification with credentials that are well-formed but invalid, it is in violation of **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Notify operational intent details changed with an incorrect scope check

If the USS under test accepts an operational intent details change notification with valid credentials but an incorrect scope, it is in violation of **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Unauthorized requests return the proper error message body check

If, for any of the rejected requests above, the USS under test does not return a proper error message body, it fails to properly implement the OpenAPI specification that is part of **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Notify operational intent details changed with valid credentials check

If the USS under test rejects an operational intent details change notification with a 401 or 403 when valid credentials with an appropriate scope are presented, it is in violation of **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

### Make USS report authentication test step

uss_qualifier submits a dummy report to the USS under test's makeUssReport endpoint using several kinds of credentials, both permitted and not permitted by [the OpenAPI specification](https://github.com/astm-utm/Protocol/blob/v1.0.0/utm.yaml#L3822-L3832).

#### ⚠️ Make USS report with missing credentials check

If the USS under test accepts a request to make a USS report without any credentials being presented, it is in violation of **[astm.f3548.v21.USS0105,4](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Make USS report with invalid credentials check

If the USS under test accepts a request to make a USS report with credentials that are well-formed but invalid, it is in violation of **[astm.f3548.v21.USS0105,4](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Make USS report with an incorrect scope check

If the USS under test accepts a request to make a USS report with valid credentials but an incorrect scope, it is in violation of **[astm.f3548.v21.USS0105,4](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Unauthorized requests return the proper error message body check

If, for any of the rejected requests above, the USS under test does not return a proper error message body, it fails to properly implement the OpenAPI specification that is part of **[astm.f3548.v21.USS0105,4](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Make USS report with valid credentials check

If the USS under test rejects a request to make a USS report with a 401 or 403 when valid credentials with an appropriate scope are presented, it is in violation of **[astm.f3548.v21.USS0105,4](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### ⚠️ Successful flight deletion check
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**
