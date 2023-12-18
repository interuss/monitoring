# Generic flight planners preparation test scenario

## Description

This scenario prepares flight planner systems for execution of controlled test scenarios by checking planner systems' readiness and having them remove any existing flights that may already be in the test area.

## Resources

### flight_planners

FlightPlannersResource listing all USSs undergoing planning tests so that they can be checked for readiness and instructed to remove any existing flights from the area in this scenario.

### mock_uss

(Optional)  MockUSSResource is checked for readiness and instructed to remove any existing flights from the area in this scenario.

### flight_intents

FlightIntentsResource containing flight intents that will be used in subsequent tests, so all planners should be instructed to clear any area involved with any of these intents of flights it manages.

### flight_intents2

(Optional) If more than one FlightIntentsResource will be used in subsequent tests, additional intents may be specified with this resource.

### flight_intents3

(Optional) If more than one FlightIntentsResource will be used in subsequent tests, additional intents may be specified with this resource.

### flight_intents4

(Optional) If more than one FlightIntentsResource will be used in subsequent tests, additional intents may be specified with this resource.

## Preparation test case

### Check for flight planning readiness test step

All USSs are queried for their readiness to ensure later tests can proceed.

#### ⚠️ Valid response to readiness query check

**[interuss.automated_testing.flight_planning.ImplementAPI](../../requirements/interuss/automated_testing/flight_planning.md)**

#### ⚠️ Flight planning USS ready check

**[interuss.automated_testing.flight_planning.Readiness](../../requirements/interuss/automated_testing/flight_planning.md)**

### Area clearing test step

All USSs are requested to remove all flights from the area under test.

#### ⚠️ Valid response to clearing query check

**[interuss.automated_testing.flight_planning.ImplementAPI](../../requirements/interuss/automated_testing/flight_planning.md)**

#### ⚠️ Area cleared successfully check

**[interuss.automated_testing.flight_planning.ClearArea](../../requirements/interuss/automated_testing/flight_planning.md)**
