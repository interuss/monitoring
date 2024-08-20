# Solo happy path test scenario

## Description
This scenario performs a simple flight planning sequence with a single USS and no interactions with other USSs.  It
verifies that basic planning functionality for the USS works properly.

It assumes that the area used in the scenario is already clear of any pre-existing flights (using, for instance,
PrepareFlightPlanners scenario).

## Resources
### flight_intents
The FlightIntentsResource must provide the following flight intents:

<table>
  <tr>
    <th>Flight intent ID</th>
    <th>Flight name</th>
    <th>Priority</th>
    <th>Airspace usage state</th>
    <th>UAS state</th>
  </tr>
  <tr>
    <td><code>flight1_planned</code></td>
    <td rowspan="2">Flight 1</td>
    <td rowspan="2">Any (but all the same)</td>
    <td>Planned</td>
    <td rowspan="2">Nominal</td>
  </tr>
  <tr>
    <td><code>flight1_activated</code></td>
    <td>InUse</td>
  </tr>
</table>

Because the scenario involves activation of intents, the start times of all activated intents must be during the time
the test scenario is executed (not before). Additionally, their end times must leave sufficient time for the execution
of the test scenario.

### tested_uss
FlightPlannerResource that is under test and will manage Flight 1 and its variants.

### dss
DSSInstanceResource that provides access to a DSS instance where flight creation/sharing can be verified.

## Prerequisites check test case

### [Verify area is clear test step](../clear_area_validation.md)

While this scenario assumes that the area used is already clear of any pre-existing flights (using, for instance, PrepareFlightPlanners scenario) in order to avoid a large number of area-clearing operations, the scenario will not proceed correctly if the area was left in a dirty state following a previous scenario that was supposed to leave the area clear.  This test step verifies that the area is clear.

## Solo happy path test case

### Plan Flight 1 test step

#### [Plan Flight 1](../../../flight_planning/plan_flight_intent.md)
Flight 1 should be successfully planned by the tested USS.

#### [Validate Flight 1 sharing](../validate_shared_operational_intent.md)

### Activate Flight 1 test step

#### [Activate Flight 1](../../../flight_planning/activate_flight_intent.md)
Flight 1 should be successfully activated by the tested USS.

#### [Validate Flight 1 sharing](../validate_shared_operational_intent.md)

### [Delete Flight 1 test step](../../../flight_planning/delete_flight_intent.md)
Flight 1 should be sucessfully removed from the system by the tested USS.

## Cleanup
### ⚠️ Successful flight deletion check
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**
