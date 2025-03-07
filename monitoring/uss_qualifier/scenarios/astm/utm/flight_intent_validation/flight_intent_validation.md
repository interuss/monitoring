# Validation of operational intents test scenario

## Description
This test checks that the USS validates correctly the operational intents it creates.
Notably the following requirements:
- **[astm.f3548.v21.OPIN0015](../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.OPIN0020](../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.OPIN0030](../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.OPIN0040](../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.GEN0500](../../../../requirements/astm/f3548/v21.md)**

It assumes that the area used in the scenario is already clear of any pre-existing flights (using, for instance, PrepareFlightPlanners scenario).

## Resources
### flight_intents
FlightIntentsResource that provides the following flight intents:

<table>
  <tr>
    <th>Flight intent ID</th>
    <th>Flight name</th>
    <th>Usage State</th>
    <th>UAS State</th>
    <th>Invalid details</th>
  </tr>
  <tr>
    <td><code>valid_flight</code></td>
    <td rowspan="2">Valid Flight</td>
    <td>Planned</td>
    <td rowspan="2">Nominal</td>
    <td rowspan="2">N/A</td>
  </tr>
  <tr>
    <td><code>valid_activated</code></td>
    <td>InUse</td>
  </tr>

  <tr>
    <td><code>valid_conflict_tiny_overlap</code></td>
    <td>Tiny Overlap Conflict Flight</td>
    <td rowspan="3">Planned</td>
    <td rowspan="3">Nominal</td>
    <td>Conflicts with Flight 1 such that their 3D volumes have an overlap just above <code>IntersectionMinimumPrecision</code> = 1cm</td>
  </tr>
  <tr>
    <td><code>invalid_too_far_away</code></td>
    <td>Too Far Away Flight</td>
    <td>Has a start time that is more than <code>OiMaxPlanHorizon</code> = 30 days ahead of time</td>
  </tr>
  <tr>
    <td><code>invalid_recently_ended</code></td>
    <td>Recently Ended Flight</td>
    <td>Has an end time that is within 5 to 10 seconds in the past.</td>
  </tr>
</table>

Because the scenario involves activation of intents, all activated intents must be active during the execution of the
test scenario. Additionally, their end time must leave sufficient time for the execution of the test scenario. For the
sake of simplicity, it is recommended to set the start and end times of all the intents to the same range.

### tested_uss
FlightPlannerResource that will be tested for its validation of operational intents.

### dss
DSSInstanceResource that provides access to a DSS instance where flight creation/sharing can be verified.

## Attempt to plan invalid flights test case
### Attempt to plan Too Far Away Flight test step
The user flight intent that the test driver attempts to plan has a start time that is more than OiMaxPlanHorizon = 30 days ahead of
time. As such, the attempt should be rejected.

#### 🛑 Incorrectly planned check
If the USS successfully plans the flight or otherwise fails to indicate a rejection, it means that it failed to validate
the intent provided.  Therefore, this check will fail if the USS indicates success in creating the flight from the user
flight intent, per **[astm.f3548.v21.OPIN0030](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Failure check
All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept the flight. If the USS indicates that the attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../requirements/interuss/automated_testing/flight_planning.md)**.

#### [Validate Too Far Away Flight not planned](../validate_not_shared_operational_intent.md)

### Attempt to plan Recently Ended Flight test step
The user flight intent that the test driver attempts to plan has recently ended by just slightly more than `TimeSyncMaxDifferentialSeconds` = 5 seconds.
As such, if the USS synchronizes its time correctly, the attempt should be rejected.

#### 🛑 Incorrectly planned check
If the USS successfully plans the flight or otherwise fails to indicate a rejection, it means that it failed to validate
that the intent provided was in the past. Therefore, this check will fail if the USS indicates success in creating the
flight from the user flight intent, per one of the following requirements:
- the USS does not implement properly the interface _getOperationalIntentDetails_ as required by **[astm.f3548.v21.USS0105,1](../../../../requirements/astm/f3548/v21.md)**, which specifies that _The end time may not be in the past_; or
- the USS did not synchronize its time within `TimeSyncMaxDifferentialSeconds` = 5 seconds of an industry-recognized time source as required by **[astm.f3548.v21.GEN0100](../../../../requirements/astm/f3548/v21.md)**; or
- the USS did not use the synchronized time for the operational intent timestamps, as required by **[astm.f3548.v21.GEN0105](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Failure check
All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept the flight. If the USS indicates that the attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../requirements/interuss/automated_testing/flight_planning.md)**.

#### [Validate Recently Ended Flight not planned](../validate_not_shared_operational_intent.md)

## Validate transition to Ended state after cancellation test case
### Plan Valid Flight test step

#### [Plan Valid Flight](../../../flight_planning/plan_flight_intent.md)
The valid flight should be successfully planned by the flight planner.

#### [Validate Valid Flight shared correctly](../validate_shared_operational_intent.md)
Validate that the flight was shared correctly and is discoverable.

### Remove Valid Flight test step

#### [Cancel Valid Flight](../../../flight_planning/delete_flight_intent.md)
The flight should be successfully transitioned to Ended state by the flight planner.

#### [Validate Valid Flight is non-discoverable](../validate_removed_operational_intent.md)

#### 🛑 Operational intent not shared check
If the operational intent is still discoverable after it was transitioned to Ended,
this check will fail per **[astm.f3548.v21.OPIN0040](../../../../requirements/astm/f3548/v21.md)**.

## Validate precision of intersection computations test case
### [Plan Valid Flight test step](../../../flight_planning/plan_flight_intent.md)
The valid flight intent should be successfully planned by the flight planner.

### Attempt to plan Tiny Overlap Conflict Flight test step
The tested USS is instructed to plan a flight that is constructed in a way that it intersects with Valid Flight by just
over `IntersectionMinimumPrecision` = 1 cm.

#### 🛑 Incorrectly planned check
If the tested USS successfully plans the flight or otherwise fails to indicate a rejection, it means that it failed
to correctly compute the conflicting intersection. Therefore, this check will fail if the USS indicates success in
planning the flight from the user flight intent, per **[astm.f3548.v21.GEN0500](../../../../requirements/astm/f3548/v21.md)**.

#### Failure check
All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept the flight. If the USS indicates that the attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../requirements/interuss/automated_testing/flight_planning.md)**.

#### [Validate Tiny Overlap Conflict Flight not planned](../validate_not_shared_operational_intent.md)

## Cleanup
### ⚠️ Successful flight deletion check
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**
