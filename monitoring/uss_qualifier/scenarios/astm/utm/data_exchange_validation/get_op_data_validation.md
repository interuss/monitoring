# Data Validation of GET operational intents by USS test scenario

## Description
This test checks that the USS being tested validates the operational intents received as response to its GET request from another USS.
Control_uss which is a mock uss plans a nearby V-shaped operation, and provides the data that tested_uss GETs.
tested_uss validates the GET response from control_uss and accordingly plan its operation.
Notably the following requirements:

- **[astm.f3548.v21.SCD0035](../../../../requirements/astm/f3548/v21.md)**

## Resources
### flight_intents
FlightIntentsResource provides the two V-shaped flight intents.
The convex hulls of the 2D footprints of the two flights intersect, but the polygons do not intersect.
There is an overlap in time and altitude of the two flights.
- flight_1
- flight_2

### control_uss
MockUSSResource that will be used for planning flights, controlling data shared for validation testing, and gathering interuss interactions from mock_uss.

### tested_uss
FlightPlannerResource that will be used for the USS being tested for its data validation of operational intent.

### dss
DSSInstanceResource that provides access to a DSS instance where flight creation/sharing can be verified.

## Setup test case
### Check for flight planning readiness test step
Both USSs are queried for their readiness to ensure this test can proceed.

#### Flight planning USS not ready check
If either USS does not respond appropriately to the endpoint queried to determine readiness, this check will fail and the USS will have failed to meet **[astm.f3548.v21.GEN0310](../../../../requirements/astm/f3548/v21.md)** as the USS does not support the InterUSS implementation of that requirement.

### Area clearing test step
Both USSs are requested to remove all flights from the area under test.

#### Area cleared successfully check
**[interuss.automated_testing.flight_planning.ClearArea](../../../../requirements/interuss/automated_testing/flight_planning.md)**

## Successfully plan flight near an existing flight test case
### [Control_uss plans flight 2 test step](../../../flight_planning/plan_flight_intent.md)
Flight 2 should be successfully planned by the control USS.

### [Validate flight 2 sharing test step](../validate_shared_operational_intent.md)
Validate that flight 2 is planned

### [Validate no notification pushed for flight 2](test_steps/validate_no_notification_operational_intent.md)
Check there is no subscription by tested_uss to trigger notification of flight 2.
If no notification is pushed by control_uss to tested_uss, we know tested_uss has no subscription.
This will ensure that while planning a nearby flight, tested_uss will need to make a GET request to control_uss for flight 2 details.
If this notification was pushed, the GET operational intent data validation test cannot be done.

#### MockUSS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.

#### Expect Notification not sent check
As there is no subscription expected, no notification of operational_intent should be sent.
**[interuss.f3548.notification_requirements.NoSubscriptionNoNotification](../../../../requirements/interuss/f3548/notification_requirements.md)**


### [Tested_uss plans flight 1 test step](../../../flight_planning/plan_flight_intent.md)
The test driver attempts to plan flight 1 via the tested USS. It checks if any conflicts with flight 2
which is of equal priority and came first.

### [Validate flight 1 sharing test step](../validate_shared_operational_intent.md)
Validate flight 1 is planned.

### [Validate flight2 GET interaction test step](test_steps/validate_get_operational_intent.md)
Tested_uss needs to make GET request for obtaining details of flight 2.
In a previous step(Validate no notification pushed for flight 2), we checked there was no notification of flight 2 to tested_uss.

### [Validate flight1 Notification sent to Control_uss test step](test_steps/validate_notification_operational_intent.md)
Tested_uss notifies flight 1 to Control_uss, due to its subscription through flight 2.

### [Delete tested_uss flight test step](../../../flight_planning/delete_flight_intent.md)
Teardown

### [Delete control_uss flight test step](../../../flight_planning/delete_flight_intent.md)
Teardown

## Flight planning prevented due to invalid data sharing test case
### [Control_uss plans flight 2, sharing invalid operational intent data test step](../../../flight_planning/plan_flight_intent.md)
Flight 2 should be successfully planned by the control_uss.
The control_uss, which is mock_uss is instructed to share invalid data with other USS, for negative test.

### [Validate flight 2 shared operational intent with invalid data test step](test_steps/validate_sharing_operational_intent_but_with_invalid_interuss_data.md)
Validate that flight 2 is shared with invalid data as a modified behavior is injected by uss_qualifier for a negative test.

### [Validate no notification pushed for flight 2](test_steps/validate_no_notification_operational_intent.md)
Check there is no subscription by tested_uss to trigger notification of flight 2.
If no notification is pushed by control_uss to tested_uss, we know tested_uss has no subscription.
This will ensure that while planning a nearby flight, tested_uss will need to make a GET request to control_uss for flight 2 details.
If this notification was pushed, the GET operational intent data validation test cannot be done.

#### MockUSS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.

#### Expect Notification not sent check
As there is no subscription expected, no notification of operational_intent should be sent.
**[interuss.f3548.notification_requirements.NoSubscriptionNoNotification](../../../../requirements/interuss/f3548/notification_requirements.md)**


### [Test_uss attempts to plan flight 1, expect failure test step](test_steps/plan_flight_intent_expect_failed.md)
The test driver attempts to plan the flight 1 via the tested_uss. It checks if any conflicts with flight 2
which is of equal priority and came first.

### [Validate flight 1 not shared by tested_uss test step](../validate_not_shared_operational_intent.md)
Validate flight 1 is not shared with DSS, as plan failed.

### [Validate flight 2 GET interaction test step](test_steps/validate_get_operational_intent.md)
Tested_uss needs to make GET request for obtaining details of flight 2 from control_uss.
In a previous step(Validate no notification pushed for flight 2), we checked there was no notification of flight 2 to tested_uss.
Hence USS will have to obtain details using GET request.

### [Validate flight 1 Notification not sent to Control_uss test step](test_steps/validate_no_notification_operational_intent.md)

### [Delete Control_uss flight test step](../../../flight_planning/delete_flight_intent.md)
Teardown

## Cleanup
### Successful flight deletion check
This cleanup is for both - after testcase ends and after test scenario ends
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**
