# Data Validation of GET operational intents by USS test scenario

## Description
This test checks that the USS being tested validates the operational intents received as response to its GET request from another USS.
mock_uss plans a nearby V-shaped operation, and provides the data that tested_uss GETs.
tested_uss validates the GET response from mock_uss and accordingly plan its operation.
Notably the following requirements:

- **[astm.f3548.v21.SCD0035](../../../../requirements/astm/f3548/v21.md)**

This scenario assumes that the area used in the scenario is already clear of any pre-existing flights (using, for instance, PrepareFlightPlanners scenario).

## Resources
### flight_intents
FlightIntentsResource provides the two V-shaped flight intents.
The convex hulls of the 2D footprints of the two flights intersect, but the polygons do not intersect.
There is an overlap in time and altitude of the two flights.
- flight_1
- flight_2

### mock_uss
MockUSSResource that will be used for planning flights, controlling data shared for validation testing, and gathering interuss interactions from mock_uss.

### tested_uss
FlightPlannerResource that will be used for the USS being tested for its data validation of operational intent.

### dss
DSSInstanceResource that provides access to a DSS instance where flight creation/sharing can be verified.

## Successfully plan flight near an existing flight test case

### [mock_uss plans flight 2 test step](../../../flight_planning/plan_flight_intent.md)
Flight 2 should be successfully planned by the control USS.

### [Validate flight 2 sharing test step](../validate_shared_operational_intent.md)
Validate that flight 2 is planned

### [tested_uss plans flight 1 test step](../../../flight_planning/plan_flight_intent.md)
The test driver attempts to plan flight 1 via the tested USS. It checks if any conflicts with flight 2
which is of equal priority and came first.

### [Validate flight 1 sharing test step](../validate_shared_operational_intent.md)
Validate flight 1 is planned.

### Check for notification to tested_uss due to subscription in flight 2 area test step
In the following test step, we want to assert that tested_uss must have retrieved operational intent details from
mock_uss via a GET request.  This assertion is only valid, however, if tested_uss did not obtain the  operational
intent details in a different way -- specifically, a notification due to a pre-existing subscription.  In this test
step, we determine if tested_uss had a pre-existing subscription by:

#### [checking if mock_uss sent a notification to tested_uss](test_steps/query_mock_uss_interactions.md)

### [Validate flight2 GET interaction, if no notification test step](test_steps/validate_get_operational_intent.md)
This step is skipped if a notification to tested_uss was found in the previous step.

### [Validate flight1 Notification sent to mock_uss test step](test_steps/validate_notification_operational_intent.md)
tested_uss notifies flight 1 to mock_uss, due to its subscription through flight 2.

### [Delete tested_uss flight test step](../../../flight_planning/delete_flight_intent.md)
Teardown

### [Delete mock_uss flight test step](../../../flight_planning/delete_flight_intent.md)
Teardown

## Flight planning prevented due to invalid data sharing test case
### [mock_uss plans flight 2, sharing invalid operational intent data test step](../../../flight_planning/plan_flight_intent.md)
Flight 2 should be successfully planned by the mock_uss.
The mock_uss is instructed to share invalid data with other USS, for negative test.

### [Validate flight 2 shared operational intent with invalid data test step](test_steps/validate_sharing_operational_intent_but_with_invalid_interuss_data.md)
Validate that flight 2 is shared with invalid data as a modified behavior is injected by uss_qualifier for a negative test.

### [tested_uss attempts to plan flight 1, expect failure test step](test_steps/plan_flight_intent_expect_failed.md)
The test driver attempts to plan the flight 1 via the tested_uss. It checks if any conflicts with flight 2
which is of equal priority and came first.

### [Validate flight 1 not shared by tested_uss test step](../validate_not_shared_operational_intent.md)
Validate flight 1 is not shared with DSS, as plan failed.

### Check for notification to tested_uss due to subscription in flight 2 area test step
In the following test step, we want to assert that tested_uss must have retrieved operational intent details from
mock_uss via a GET request.  This assertion is only valid, however, if tested_uss did not obtain the  operational
intent details in a different way -- specifically, a notification due to a pre-existing subscription.  In this test
step, we determine if tested_uss had a pre-existing subscription by:

#### [checking if mock_uss sent a notification to tested_uss](test_steps/query_mock_uss_interactions.md)

### [Validate flight2 GET interaction, if no notification test step](test_steps/validate_get_operational_intent.md)
This step is skipped if a notification to tested_uss was found in the previous step.

### [Validate flight 1 Notification not sent to mock_uss test step](test_steps/validate_no_notification_operational_intent.md)

### [Delete mock_uss flight test step](../../../flight_planning/delete_flight_intent.md)
Teardown

## Cleanup
### Successful flight deletion check
This cleanup is for both - after testcase ends and after test scenario ends
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**
