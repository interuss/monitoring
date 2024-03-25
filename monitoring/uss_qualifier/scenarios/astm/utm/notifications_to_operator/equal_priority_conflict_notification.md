# Notifications to operator: equal priority conflict notification to new or modified operational intent test scenario

## Description
This test aims at testing the strategic coordination requirements that relate to the notification scenarios where
there exists a conflict with an equal priority flight and the operator of a new or modified operational intent is notified:
- **[astm.f3548.v21.OPIN0025](../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.SCD0035](../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.SCD0040](../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.SCD0090](../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.USS0005](../../../../requirements/astm/f3548/v21.md)**

It involves a tested USS and a control USS through which a conflicting flight is injected.

This scenario skips execution and completes successfully at the setup case if a resource containing equal priority flight intents where conflicts are not allow is not provided, such as if a jurisdiction does not have any priority levels at which conflicts are not allowed.

It assumes that the area used in the scenario is already clear of any pre-existing flights (using, for instance, PrepareFlightPlanners scenario).

## Sequence Diagram
![Sequence diagram for SCD0090](/assets/SCD90_no_priority.png)

## Resources
### flight_intents
If the jurisdiction in which these tests are being conducted does not have a priority level at which conflicts are not allowed, the FlightIntentsResource must be None to prevent the
execution of this test.

Otherwise, the FlightIntentsResource must provide the following flight intents:

<table>
  <tr>
    <th>Flight intent ID</th>
    <th>Flight name</th>
    <th>Priority</th>
    <th>State</th><!-- TODO: Update with usage_state and uas_state when new flight planning API is adopted -->
    <th>Must conflict with</th>
    <th>Must not conflict with</th>
  </tr>
  <tr>
    <td><code>flight1_planned</code></td>
    <td>Flight 1</td>
    <td rowspan="3">Any (but all the same)</td>
    <td>Planned</td>
    <td>Flight 2</td>
    <td>N/A</td>
  </tr>
  <tr>
    <td><code>flight1c_planned</code></td>
    <td>Flight 1c</td>
    <td rowspan="2">Accepted</td>
    <td>N/A</td>
    <td>Flight 2</td>
  </tr>
  <tr>
    <td><code>equal_prio_flight2_planned</code></td>
    <td>Flight 2</td>
    <td>Flight 1</td>
    <td>Flight 1c</td>
  </tr>
</table>

### tested_uss
FlightPlannerResource that is under test and will manage Flight 1 and its variants.

### control_uss
FlightPlannerResource that will be used to inject conflicting Flight 2.

### dss
DSSInstanceResource that provides access to a DSS instance where flight creation/sharing can be verified.


## Attempt to plan flight into conflict test case
![Test case summary illustration](../nominal_planning/conflict_equal_priority_not_permitted/assets/attempt_to_plan_flight_into_conflict.svg)

### Plan Flight 2 test step

#### [Plan Flight 2](../../../flight_planning/plan_flight_intent.md)
Flight 2 should be successfully planned by the control USS.

#### [Validate Flight 2 sharing](../validate_shared_operational_intent.md)

### Attempt to plan Flight 1 test step

#### [Attempt to plan Flight 1](../../../flight_planning/plan_conflict_flight_intent.md)
The test driver attempts to plan the Flight 1 via the tested USS. However, it conflicts with Flight 2
which is of equal priority but came first. As such it should be rejected
per **[astm.f3548.v21.SCD0035](../../../../requirements/astm/f3548/v21.md)**.

#### [Validate Flight 1 not shared](../validate_not_shared_operational_intent.md)
Flight 1 should not have been shared with the interoperability ecosystem since it was rejected.

### Validate tested USS conflict notification to user

#### [Validate tested USS conflict notification to user](test_steps/validate_conflict_notification_to_user.md)
The test driver waits 12 seconds and checks conflict notification logs of tested USS to verify that notification was sent to Flight 1 due to conflict with Flight 2.

## Attempt to modify planned flight into conflict test case
![Test case summary illustration](../nominal_planning/conflict_equal_priority_not_permitted/assets/attempt_to_modify_planned_flight_into_conflict.svg)

### Plan Flight 1c test step

#### [Plan Flight 1c](../../../flight_planning/plan_flight_intent.md)
The smaller Flight 1c form (which doesn't conflict with Flight 2) should be successfully planned by the tested USS.

#### [Validate Flight 1c sharing](../validate_shared_operational_intent.md)

### Attempt to modify planned Flight 1c into conflict test step

#### [Attempt to modify Flight 1c](../../../flight_planning/modify_planned_conflict_flight_intent.md)
The test driver attempts to enlarge Flight 1c so that it conflicts with Flight 2.
However, Flight 2 is of equal priority but was planned first.
As such the change to Flight 1c should be rejected per **[astm.f3548.v21.SCD0040](../../../../requirements/astm/f3548/v21.md)**.

#### [Validate Flight 1c not modified](../validate_shared_operational_intent.md)
Because the modification attempt was invalid, either Flight 1c should not have been modified (because the USS kept the original accepted request), or it should have been removed (because the USS rejected the replacement plan provided).

### Validate tested USS conflict notification to user

#### [Validate tested USS conflict notification to user](test_steps/validate_conflict_notification_to_user.md)
The test driver waits 12 seconds and checks conflict notification logs of tested USS to verify that notification was sent to Flight 1c due to conflict with Flight 2.

## Cleanup
### [Delete Flight 2 test step](../../../flight_planning/delete_flight_intent.md)
Remove Flight 2 from the system.

### [Delete Flight 1c test step](../../../flight_planning/delete_flight_intent.md)
Remove Flight 1c from the system.
