# Flight authorisation validation test scenario

## Description

This test attempts to create flights with invalid values provided for various
fields needed for a U-space flight authorisation, followed by successful flight
creation when all fields are valid.

It assumes that the area used in the scenario is already clear of any
pre-existing flights (using, for instance, PrepareFlightPlanners scenario).

## Sequence

![Sequence diagram](sequence.png)

## Resources

### flight_intents
FlightIntentsResource that provides the following flight intents:

<table>
  <tr>
    <th>Flight intent ID</th>
    <th>Flight name</th>
    <th>Usage State</th>
    <th>UAS State</th>
    <th>Flight authorisation</th>
  </tr>
  <tr>
    <td><code>valid_flight_intent</code></td>
    <td>Valid Flight</td>
    <td rowspan="2">Planned</td>
    <td rowspan="2">Nominal</td>
    <td>Valid</td>
  </tr>
  <tr>
    <td><code>invalid_*</code></td>
    <td>Invalid Flight *</td>
    <td>Invalid</td>
  </tr>
</table>

### flight_planner

FlightPlannerResource that provides the flight planner (USSP) which should be tested.

## Attempt invalid flights test case

### Inject invalid flight intents test step

uss_qualifier indicates to the first flight planner a user intent to create each of the invalid flight intents expecting the flight planner to reject each of these intents.

#### 🛑 Incorrectly planned check

Each of the attempted flight intents contains invalid flight authorisation data.  If the USSP successfully plans the flight, it means they failed to detect the invalid flight authorisation.  Therefore, this check will fail if the USS indicates success in creating the flight from the user flight intent.

#### ⚠️ Failure check

Although the flight authorisation data is invalid, it is properly formatted and should allow the USSP to process it and reject the flight rather than causing a failure.  If the USS indicates that the injection attempt failed, this check will fail.

## Plan valid flight test case

### [Plan valid flight intent test step](../../flight_planning/plan_flight_intent.md)

uss_qualifier indicates to the flight planner a user intent to create a valid flight.

## Cleanup

### 🛑 Successful flight deletion check

**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../requirements/interuss/automated_testing/flight_planning.md)**
