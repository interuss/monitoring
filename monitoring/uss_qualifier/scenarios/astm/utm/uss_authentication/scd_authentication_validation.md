# ASTM SCD USS: Interfaces authentication test scenario

## Overview

Ensures that a USS rejects improperly-authenticated requests to the strategic coordination endpoints required by **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**, and **[astm.f3548.v21.USS0105,4](../../../../requirements/astm/f3548/v21.md)**.

## Resources

### tested_uss

[`FlightPlannerResource`](../../../../resources/flight_planning/flight_planners.py) for the USS under test.

### utm_auth

[`AuthAdapterResource`](../../../../resources/communications/auth_adapter.py) used to obtain credentials when acting as a peer USS.

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) used to find the operational intent reference created by the USS under test, which provides the USS base URL.

### flight_intents

[`FlightIntentsResource`](../../../../resources/flight_planning/flight_intents_resource.py) providing `flight_1`, a nominal flight planned by the USS under test so that its base URL can be discovered.

## Setup test case

### Successfully plan flight test step

#### [Plan successfully](../../../flight_planning/plan_flight_intent.md)

#### [Validate operational intent is shared](../validate_shared_operational_intent.md)

## Endpoint authorization test case

This test case ensures that the USS properly authenticates requests to its strategic coordination endpoints.

### Operational Intent endpoints authentication test step

#### 🛑 Unauthorized requests return the proper error message body check

If the USS under test does not return a proper error message body when an unauthorized request is received, it fails to properly implement the OpenAPI specification that is part of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get operational intent details with missing credentials check

If the USS under test allows the fetching of operational intent details without any credentials being presented, it is in violation of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get operational intent details with invalid credentials check

If the USS under test allows the fetching of operational intent details with credentials that are well-formed but invalid, it is in violation of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get operational intent details with incorrect scope check

If the USS under test allows the fetching of operational intent details with valid credentials but an incorrect scope, it is in violation of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get operational intent details with valid credentials check

If the USS under test rejects a request to fetch operational intent details with a 401 or 403 when valid credentials with an appropriate scope are presented, it is in violation of **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Notify operational intent details changed with missing credentials check

If the USS under test accepts an operational intent details change notification without any credentials being presented, it is in violation of **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Notify operational intent details changed with invalid credentials check

If the USS under test accepts an operational intent details change notification with credentials that are well-formed but invalid, it is in violation of **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Notify operational intent details changed with incorrect scope check

If the USS under test accepts an operational intent details change notification with valid credentials but an incorrect scope, it is in violation of **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Notify operational intent details changed with valid credentials check

If the USS under test rejects an operational intent details change notification with a 401 or 403 when valid credentials with an appropriate scope are presented, it is in violation of **[astm.f3548.v21.USS0105,3](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### ⚠️ Successful flight deletion check
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**
