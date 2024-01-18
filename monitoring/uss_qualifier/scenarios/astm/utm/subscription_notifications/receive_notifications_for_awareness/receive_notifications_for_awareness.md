# USS Awareness of Relevant Operational Intent Changes When Managing Operational Intents test scenario

## Description
A USS under test, creates a subscription to maintain awareness of the relevant operational intents,
when it submits an operational intent to DSS. This helps it to be notified of new or modified operations
in the area, when its operational intent is in Activated, NonConforming and Contingent state. In this scenario,
we will verify that USS under test creates a subscription to cover the operational intent area, and receives notifications from other USSes.

- **[astm.f3548.v21.SCD0080](../../../../../requirements/astm/f3548/v21.md)**

This scenario assumes that the area used in the scenario is already clear of any pre-existing flights (using, for instance, PrepareFlightPlanners scenario).

## Resources
### flight_intents
FlightIntentsResource provides the two V-shaped flight intents and one flight intent that is modified to extend its area.
The convex hulls of the 2D footprints of the flight_2 and flight_1 intersect, but the polygons do not intersect.
The convex hulls of the 2D footprints of the flight_3 and flight_1_extended intersect, but the polygons do not intersect.
There is an overlap in time and altitude of flight_2 and flight_3 with flight_1.
- flight_1
- flight_1_extended
- flight_1_non_conforming
- flight_1_contingent
- flight_2
- flight_3

### mock_uss
MockUSSResource will be used for planning flights in order to send notifications to tested_uss, and gathering interuss interactions from mock_uss.

### tested_uss
FlightPlannerResource that will be used for the USS being tested for its ability to maintain awareness of operational intent.

### dss
DSSInstanceResource that provides access to a DSS instance where flight creation/sharing can be verified.

## Activate operational intent and receive notification of relevant intent test case

### tested_uss plans flight1 test step

#### [Plan flight1](../../../../flight_planning/plan_flight_intent.md)
Flight 2 should be successfully planned by the control USS.

#### [Validate flight 1 sharing](../../validate_shared_operational_intent.md)

#### Find the subscription id for flight1

### Activate flight1 test step

#### [Activate flight1](../../../../flight_planning/activate_flight_intent.md)
Flight 1 should be successfully activated by the control USS.

#### [Validate flight1 sharing](../../validate_shared_operational_intent.md)

### mock_uss plans flight2 test step

#### [Plan](../../../../flight_planning/plan_flight_intent.md)

The test driver plans flight2 via the mock uss.

#### [Validate flight2 sharing](../../validate_shared_operational_intent.md)

### [Validate flight2 notification received by tested_uss test step](../test_steps/validate_notification_received.md)
mock_uss notifies flight 2 to tested_uss, with flight1 subscription id.


## Modify Activated operational intent area and receive notification of relevant intent test case

### tested_uss modifies flight1 test step

#### [Modify flight1](../../../../flight_planning/modify_activated_flight_intent.md)
Flight1 should be successfully modified with its area extended by the tested USS.

#### [Validate flight 1 sharing](../../validate_shared_operational_intent.md)

#### Find the subscription id for flight1
Could be a new subscription id, or the same.
The subscription will be modified to include the extended area, if it did not already include it.

### Activate flight1 test step

### mock_uss plans flight3 test step

#### [Plan](../../../../flight_planning/plan_flight_intent.md)

The test driver plans flight3 via the mock uss. This intent intersects the extended part of flight1.

#### [Validate flight3 sharing](../../validate_shared_operational_intent.md)

### [Validate flight3 notification received by tested_uss test step](../test_steps/validate_notification_received.md)
mock_uss notifies flight 3 to tested_uss, with flight1 subscription id.

## Operational intent declared non conforming and receive notification of relevant intent test case

### Declare Flight1 non-conforming test step
The test driver instructs the tested USS to declare Flight 1 as non-conforming.

Do note that executing this test step requires the control USS to support the CMSA role. As such, if the USS rejects the
transition to non-conforming state, it will be assumed that the control USS does not support this role and the test
execution will stop without failing.

#### ℹ️ Successful transition to non-conforming state check
All flight intent data provided is correct, therefore it should have been
transitioned to non-conforming state by the USS
per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.
If the USS indicates a conflict, this check will fail. If the USS indicates that the injection attempt failed, this check will fail.

#### Find the subscription id for flight1

### mock_uss modifies flight2 test step

#### [Modify](../../../../flight_planning/modify_planned_flight_intent.md)

The test driver modifies flight2 altitude via the mock uss.

#### [Validate flight2 sharing](../../validate_shared_operational_intent.md)

### [Validate flight2 notification received by tested_uss test step](../test_steps/validate_notification_received.md)
mock_uss notifies flight 2 to tested_uss, with flight1 subscription id.


## Operational intent declared contingent and receives notification of relevant intent test case

### Declare Flight1 contingent test step
The test driver instructs the tested USS to declare Flight 1 as contingent.

Do note that executing this test step requires the control USS to support the CMSA role. As such, if the USS rejects the
transition to contingent state, it will be assumed that the control USS does not support this role and the test
execution will stop without failing.

#### ℹ️ Successful transition to contingent state check
All flight intent data provided is correct, therefore it should have been
transitioned to contingent state by the USS
per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.
If the USS indicates a conflict, this check will fail. If the USS indicates that the injection attempt failed, this check will fail.

#### Find the subscription id for flight1

### mock_uss modifies flight2 test step

#### [Modify](../../../../flight_planning/modify_planned_flight_intent.md)

The test driver modifies flight2 altitude via the mock uss.

#### [Validate flight2 sharing](../../validate_shared_operational_intent.md)

### [Validate flight2 notification received by tested_uss test step](../test_steps/validate_notification_received.md)
mock_uss notifies flight 2 to tested_uss, with flight1 subscription id.

## Cleanup
### Successful flight deletion check
This cleanup is for both - after testcase ends and after test scenario ends
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../****../../../../requirements/interuss/automated_testing/flight_planning.md)**
