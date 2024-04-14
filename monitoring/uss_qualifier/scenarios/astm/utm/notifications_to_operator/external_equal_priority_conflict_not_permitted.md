# Nominal planning: not permitted conflict with equal priority test scenario

## Description
This test aims at testing the strategic coordination requirements that relate to the prioritization scenarios where
there exists a conflict with an equal priority flight that is not permitted by regulation:
- **[astm.f3548.v21.OPIN0025](../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.SCD0035](../../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.SCD0045](../../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.SCD0095](../../../../../requirements/astm/f3548/v21.md)**
- **[astm.f3548.v21.USS0005](../../../../requirements/astm/f3548/v21.md)**

It involves a tested USS and a control USS through which conflicting flights are injected.

This scenario skips execution and completes successfully at the setup case if a resource containing equal priority flight intents where conflicts are not allow is not provided, such as if a jurisdiction does not have any priority levels at which conflicts are not allowed.

It assumes that the area used in the scenario is already clear of any pre-existing flights (using, for instance, PrepareFlightPlanners scenario).

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

Because the scenario involves activation of intents, all activated intents must be active during the execution of the
test scenario. Additionally, their end time must leave sufficient time for the execution of the test scenario. For the
sake of simplicity, it is recommended to set the start and end times of all the intents to the same range.

### tested_uss
FlightPlannerResource that will be used to inject control Flight 2. 

### control_uss
FlightPlannerResource that is under test and will manage conflicting Flight 1 and its variant. Note that this control USS needs to support the
CMSA role in order to transition to the `Nonconforming` state in order to create a pre-existing conflict among equal-priority operational intents.

### dss
DSSInstanceResource that provides access to a DSS instance where flight creation/sharing can be verified.


## Prerequisites check test case

### [Verify area is clear test step](../../clear_area_validation.md)

While this scenario assumes that the area used is already clear of any pre-existing flights (using, for instance, PrepareFlightPlanners scenario) in order to avoid a large number of area-clearing operations, the scenario will not proceed correctly if the area was left in a dirty state following a previous scenario that was supposed to leave the area clear.  This test step verifies that the area is clear.

## Attempt to plan flight into conflict test case
![Test case summary illustration](../nominal_planning/conflict_equal_priority_not_permitted/assets/attempt_to_plan_flight_into_conflict.svg)

### Plan Flight 2 test step

#### [Plan Flight 2](../../../flight_planning/plan_flight_intent.md)
Flight 2 should be successfully planned by the tested USS.

#### [Validate Flight 2 sharing](../validate_shared_operational_intent.md)

### Activate Flight 2 test step

#### [Activate Flight 2](../../../flight_planning/activate_flight_intent.md)
Flight 2 should be successfully activated by the tested USS.

#### [Validate Flight 2 sharing](../validate_shared_operational_intent.md)

### Create non-conforming Flight 1 test step
The test driver instructs the control USS to create Flight 1 as non-conforming. This makes non-conforming Flight 1 conflict with activated Flight 2 -- this same-priority conflict would not be allowed if Flight 1 were in a nominal state.

Do note that executing this test step requires the tested USS to support the CMSA role. As such, if the USS rejects the creation 
of the non-conforming state, it will be assumed that the tested USS does not support this role and the test
execution will stop without failing.

#### 🛑 Failure check
All flight intent data provided is correct, therefore it should have been
created in the non-conforming state by the USS
per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../requirements/interuss/automated_testing/flight_planning.md)**.
If the USS indicates that the injection attempt failed, this check will fail.

#### [Validate Flight 1 sharing](../validate_shared_operational_intent.md)

### Record time and flight status test step
#### [Record time and flight status](../nominal_planning/conflict_equal_priority_not_permitted/test_steps/record_status_for_notification_check.md)
Record the time and flight status data for use in verifying notifications later.


### [Delete Flight 1 test step](../../../flight_planning/delete_flight_intent.md)
To prepare for the next test case, Flight 1 must be removed from the system.


## Attempt to modify planned flight into conflict test case
![Test case summary illustration](../nominal_planning/conflict_equal_priority_not_permitted/assets/attempt_to_modify_planned_flight_into_conflict.svg)

### Plan Flight 1c test step

#### [Plan Flight 1c](../../../flight_planning/plan_flight_intent.md)
The smaller Flight 1c form (which doesn't conflict with Flight 2) should be successfully planned by the control USS.

#### [Validate Flight 1c sharing](../validate_shared_operational_intent.md)

### Modify Flight 1 to non-conforming state test step
The test driver instructs the control USS to modify Flight 1c into a larger non-conforming state. This makes non-conforming Flight 1 conflict with activated Flight 2 -- this same-priority conflict would not be allowed if Flight 1 were in a nominal state.

Do note that executing this test step requires the tested USS to support the CMSA role. As such, if the USS rejects the modification 
to the non-conforming state, it will be assumed that the tested USS does not support this role and the test
execution will stop without failing.

#### 🛑 Failure check
All flight intent data provided is correct, therefore it should have been
modified to the non-conforming state by the USS
per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../requirements/interuss/automated_testing/flight_planning.md)**.
If the USS indicates that the injection attempt failed, this check will fail.

#### [Validate Flight 1 sharing](../validate_shared_operational_intent.md)

### Record time and flight status test step
#### [Record time and flight status](../nominal_planning/conflict_equal_priority_not_permitted/test_steps/record_status_for_notification_check.md)
Record the time and flight status data for use in verifying notifications later.

### Validate tested USS conflict notification to user

#### [Validate tested USS conflict notification to user](test_steps/validate_conflict_notification_to_user.md)
The test driver checks conflict notification logs of tested USS to verify that notification was sent to Flight 2 due to conflict with Flight 1 from case "Attempt to plan flight into conflict test case".
The test driver also verifies that notification was sent to Flight 1c due to conflict with Flight 2 from case "Attempt to modify planned flight into conflict test case".

## Cleanup
### ⚠️ Successful flight deletion check
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**
