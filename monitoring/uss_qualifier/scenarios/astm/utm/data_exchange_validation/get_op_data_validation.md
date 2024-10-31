# Data Validation of GET operational intents by USS test scenario

## Description
This test checks that the USS being tested validates the operational intents received as response to its GET request from another USS.
mock_uss plans an operation designed to be relevant to (but not intersect) the operation tested_uss will plan, and provides the data that tested_uss GETs.
tested_uss validates the GET response from mock_uss and accordingly plan its operation.

The primary requirement tested by this scenario is **[astm.f3548.v21.SCD0035](../../../../requirements/astm/f3548/v21.md)** because a USS cannot verify its operational intent does not conflict when it cannot obtain valid details for that operational intent.

This scenario assumes that the area used in the scenario is already clear of any pre-existing flights (using, for instance, PrepareFlightPlanners scenario).

## Resources
### flight_intents
FlightIntentsResource provides the two flight intents which must be relevant to each other, but must not intersect.
This can generally be accomplished when the convex hulls of the 2D footprints of the two flights intersect, but the polygons do not intersect.
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

### mock_uss plans flight 2 test step

#### [Plan successfully](../../../flight_planning/plan_flight_intent.md)

Flight 2 should be successfully planned by mock_uss.

#### [Validate operational intent is shared](../validate_shared_operational_intent.md)

### tested_uss plans flight 1 test step

#### [Plan successfully](../../../flight_planning/plan_flight_intent.md)

The test driver instructs tested_uss to attempt to plan flight 1. tested_uss checks if any conflicts with flight 2
which is of equal priority and came first.

#### [Validate operational intent is shared](../validate_shared_operational_intent.md)

### [Validate that tested_uss obtained flight2 details test step](test_steps/validate_operational_intent_details_obtained.md)
Validate that tested_uss obtained flight2 details from mock_uss, by means of either
a notification pushed by mock_uss to tested_uss due to the pre-existing subscription, or
direct retrieval by tested_uss from mock_uss.

### [Validate flight1 Notification sent to mock_uss test step](test_steps/validate_notification_operational_intent.md)
tested_uss notifies mock_uss of flight 1, due to mock_uss's subscription covering flight 2 (which is necessarily relevant to flight 1 per test design).

### [Delete tested_uss flight test step](../../../flight_planning/delete_flight_intent.md)

To prepare for the next test case, tested_uss's flight 1 is closed.

### [Delete mock_uss flight test step](../../../flight_planning/delete_flight_intent.md)

To prepare for the next test case, mock_uss's flight 2 is closed.

## Flight planning prevented due to invalid data sharing test case

In this test case, mock_uss is manipulated to share invalid operational intent details which should prevent tested_uss from planning since it cannot verify the absence of a conflict.

### mock_uss plans flight 2, sharing invalid operational intent data test step

#### [Plan successfully](../../../flight_planning/plan_flight_intent.md)

Flight 2 should be successfully planned by the mock_uss.

#### [Validate invalid operational intent details shared](test_steps/validate_sharing_operational_intent_but_with_invalid_interuss_data.md)

The mock_uss is instructed to share invalid data with other USS, for negative test.

### tested_uss attempts to plan flight 1, expect failure test step

#### [Plan unsuccessfully](test_steps/plan_flight_intent_expect_failed.md)

The test driver instructs tested_uss to plan flight 1. tested_uss should (per SCD0035) check if any conflicts with flight 2
which is of equal priority and came first.
The planning attempt should fail because tested_uss will be unable to obtain valid operational intent details for flight 2.

#### [Validate operational intent not shared](../validate_not_shared_operational_intent.md)

Validate flight 1 is not shared with DSS, as plan failed.

### [Validate that tested_uss obtained flight2 details test step](test_steps/validate_operational_intent_details_obtained.md)
Validate that tested_uss obtained flight2 details from mock_uss, by means of either
a notification pushed by mock_uss to tested_uss due to the pre-existing subscription, or
direct retrieval by tested_uss from mock_uss.

### [Validate flight 1 Notification not sent to mock_uss test step](test_steps/validate_no_notification_operational_intent.md)

### [Delete mock_uss flight test step](../../../flight_planning/delete_flight_intent.md)
Teardown

## Cleanup
### Successful flight deletion check
This cleanup is for both - after testcase ends and after test scenario ends
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**
