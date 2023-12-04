# ASTM F3548 flight planners preparation test scenario

## Description

This scenario prepares flight planner systems for execution of controlled test scenarios by checking planner systems' readiness and having them remove any existing flights that may already be in the test area.

## Resources

### flight_planners

FlightPlannersResource listing all USSs undergoing planning tests so that they can be checked for readiness and instructed to remove any existing flights from the area in this scenario.

### mock_uss

(Optional) MockUSSResource is checked for readiness and instructed to remove any existing flights from the area in this scenario.

### dss

DSSInstanceResource to check for lingering operational intents after the area has been cleared.

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

**[interuss.automated_testing.flight_planning.ImplementAPI](../../../requirements/interuss/automated_testing/flight_planning.md)**

#### ⚠️ Flight planning USS ready check

This readiness indicates the USS's ability to inject test data, so if this check fails, not only has the USS not met **[interuss.automated_testing.flight_planning.Readiness](../../../requirements/interuss/automated_testing/flight_planning.md)**, but it also does not meet **[astm.f3548.v21.GEN0310](../../../requirements/astm/f3548/v21.md)**.

### Area clearing test step

All USSs are requested to remove all flights from the area under test.

#### ⚠️ Valid response to clearing query check

**[interuss.automated_testing.flight_planning.ImplementAPI](../../../requirements/interuss/automated_testing/flight_planning.md)**

#### ⚠️ Area cleared successfully check

**[interuss.automated_testing.flight_planning.ClearArea](../../../requirements/interuss/automated_testing/flight_planning.md)**

### Clear area validation test step

uss_qualifier verifies with the DSS that there are no operational intents remaining in the area

#### 🛑 DSS responses check

**[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**

#### 🛑 Area is clear check

If operational intents remain in the 4D area(s) following the preceding area clearing, then the current state of the test environment is not suitable to conduct tests so this check will fail.
