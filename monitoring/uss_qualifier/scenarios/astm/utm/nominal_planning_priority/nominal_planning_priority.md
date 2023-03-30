# Nominal planning with priority test scenario

## Description

This test approximates normal strategic coordination where a user successfully
plans a flight whose operational intent is shared with other USSs, and where
another user takes priority over the first flight with an operational intent
with higher priority.

## Sequence

![Sequence diagram](sequence.png)

## Resources

### flight_intents
FlightIntentsResource that provides the 4 following flight intents:
- `first_flight`: will be planned normally
  - `first_flight_activated`: state mutation `Activated`
- `priority_flight`: will be planned on top of `first_flight`
  - `priority_flight_activated`: state mutation `Activated`
  - must intersect `first_flight`
  - must have higher priority than `first_flight`


### uss1

FlightPlannerResource that will successfully plan the first flight.

### uss2

FlightPlannerResource that will successfully plan the second, higher-priority flight over the first one.

### dss

DSSInstanceResource that provides access to a DSS instance where flight creation/sharing can be verified.

## Setup test case

### Check for necessary capabilities test step

Both USSs are queried for their capabilities to ensure this test can proceed.

#### Valid responses check

If either USS does not respond appropriately to the endpoint queried to determine capability, this check will fail.

#### Support BasicStrategicConflictDetection check

This check will fail if the first flight planner does not support BasicStrategicConflictDetection per **[astm.f3548.v21.GEN0310](../../../../requirements/astm/f3548/v21.md)** as the USS does not support the InterUSS implementation of that requirement.  If the second flight planner does not support HighPriorityFlights, this scenario will end normally at this point.

### Area clearing test step

Both USSs are requested to remove all flights from the area under test.

#### Area cleared successfully check

**[interuss.automated_testing.flight_planning.ClearArea](../../../../requirements/interuss/automated_testing/flight_planning.md)**

## Plan first flight test case

### [Plan flight intent test step](../../../flight_planning/plan_flight_intent.md)

The first flight intent should be successfully planned by the first flight planner.

### [Validate flight sharing test step](../validate_shared_operational_intent.md)

## Plan priority flight test case

In this step, the second USS executes a user intent to plan a priority flight that conflicts with the first flight.

### [Plan flight intent test step](../../../flight_planning/plan_flight_intent.md)

The first flight intent should be successfully planned by the first flight planner.

### [Validate flight sharing test step](../validate_shared_operational_intent.md)

## Activate priority flight test case

In this step, the second USS successfully executes a user intent to activate the priority flight.

### [Activate priority flight test step](../../../flight_planning/activate_flight_intent.md)

The high-priority flight intent should be successfully activated by the first flight planner.

### [Validate flight sharing test step](../validate_shared_operational_intent.md)

## Attempt to activate first flight test case

### [Activate first flight with higher priority conflict test step](../../../flight_planning/activate_priority_conflict_flight_intent.md)

In this step, the first USS fails to activate the flight it previously created as the second USS planned and activated
a conflicting higher priority flight in the meantime.

### [Validate first flight not activated test step](../validate_shared_operational_intent.md)

## Cleanup

### Successful flight deletion check

**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**
