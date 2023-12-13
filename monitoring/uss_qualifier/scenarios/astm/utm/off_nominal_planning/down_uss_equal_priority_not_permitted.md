# Off-Nominal planning: down USS with equal priority conflicts not permitted test scenario

## Description
This test aims to test the strategic coordination requirements that relate to the down USS mechanism in the case where
equal priority conflicts are not permitted:
- **[astm.f3548.v21.SCD0010](../../../../requirements/astm/f3548/v21.md)**

It involves a single tested USS. The USS qualifier acts as a virtual USS that may have its availability set to down.

## Resources
### flight_intents
FlightIntentsResource that provides the following flight intents:

<table>
  <tr>
    <th>Flight intent ID</th>
    <th>Flight name</th>
    <th>Priority</th>
    <th>State</th><!-- TODO: Update with usage_state and uas_state when new flight planning API is adopted -->
  </tr>
  <tr>
    <td><code>flight2_planned</code></td>
    <td>Flight 2</td>
    <td>High priority</td>
    <td>Accepted</td>
  </tr>
</table>


### tested_uss
FlightPlannerResource that is under test and will manage Flight 2.

### dss
DSSInstanceResource that provides access to a DSS instance where:
- flight creation/sharing can be verified,
- the USS qualifier acting as a virtual USS can create operational intents, and
- the USS qualifier can act as an availability arbitrator.

## Setup test case
### Resolve USS ID of virtual USS test step
Make a dummy request to the DSS in order to resolve the USS ID of the virtual USS.

#### Successful dummy query check

### [Restore virtual USS availability test step](../set_uss_available.md)

### Clear operational intents created by virtual USS test step
Delete any leftover operational intents created at DSS by virtual USS.

#### Successful operational intents cleanup check
If the search for own operational intents or their deletion fail, this check fails per **[astm.f3548.v21.DSS0005](../../../../requirements/astm/f3548/v21.md)**.

## Plan Flight 2 in conflict with activated operational intent managed by down USS test case
This test case aims at testing requirement **[astm.f3548.v21.SCD0010](../../../../requirements/astm/f3548/v21.md)**.

### Virtual USS creates conflicting operational intent test step
The USS qualifier, acting as a virtual USS, creates an operational intent at the DSS with a non-working base URL.
The objective is to make the later request by the tested USS to retrieve operational intent details to fail.

#### Operational intent successfully created check
If the creation of the operational intent reference at the DSS fails, this check fails per **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Virtual USS activates conflicting operational intent test step
The USS qualifier, acting as a virtual USS, activates the operational intent previously created at the DSS with a non-working base URL.
The objective is to make the later request by the tested USS to retrieve operational intent details to fail.

#### Operational intent successfully activated check
If the activation of the operational intent reference at the DSS fails, this check fails per **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### [Declare virtual USS as down at DSS test step](../set_uss_down.md)

### Tested USS attempts to plan high-priority Flight 2 test step
The high-priority Flight 2 of the tested USS conflicts with the operational intent of the virtual USS.
However, since:
- the virtual USS is declared as down at the DSS,
- it does not respond for operational intent details, and
- the conflicting operational intent is in the 'Activated' state,
- the local regulation does not allow for equal priority conflicts at the highest priority level,
The tested USS should evaluate the conflicting operational intent as having the highest priority status allowed by the local regulation.
As such, the tested USS should reject the planning of Flight 2.

#### Incorrectly planned check
All flight intent data provided is correct and the USS should have rejected properly the planning per **[astm.f3548.v21.SCD0010](../../../../requirements/astm/f3548/v21.md)**.
If the USS indicates that the injection attempt failed, this check will fail.
If the USS successfully plans Flight 2 or otherwise fails to indicate a conflict, this check will fail.

#### Failure check
All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept Flight 2. If the USS indicates that the injection attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../requirements/interuss/automated_testing/flight_planning.md)**.

### [Validate high-priority Flight 2 not shared test step](../validate_not_shared_operational_intent.md)

### [Restore virtual USS availability at DSS test step](../set_uss_available.md)


## Plan Flight 2 in conflict with nonconforming operational intent managed by down USS test case
This test case aims at testing requirement **[astm.f3548.v21.SCD0010](../../../../requirements/astm/f3548/v21.md)**.

### Virtual USS transitions to Nonconforming conflicting operational intent test step
The USS qualifier, acting as a virtual USS, transitions to Nonconforming the operational intent previously created at the DSS with a non-working base URL.
The objective is to make the later request by the tested USS to retrieve operational intent details to fail.

#### Operational intent successfully transitioned to Nonconforming check
If the transition of the operational intent reference at the DSS fails, this check fails per **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### [Declare virtual USS as down at DSS test step](../set_uss_down.md)

### Tested USS attempts to plan high-priority Flight 2 test step
The high-priority Flight 2 of the tested USS conflicts with the operational intent of the virtual USS.
However, since:
- the virtual USS is declared as down at the DSS,
- it does not respond for operational intent details, and
- the conflicting operational intent is in the 'Nonconforming' state,
- the local regulation does not allow for equal priority conflicts at the highest priority level,
The tested USS should evaluate the conflicting operational intent as having the highest priority status allowed by the local regulation.
As such, the tested USS should reject the planning of Flight 2.

#### Incorrectly planned check
All flight intent data provided is correct and the USS should have rejected properly the planning per **[astm.f3548.v21.SCD0010](../../../../requirements/astm/f3548/v21.md)**.
If the USS indicates that the injection attempt failed, this check will fail.
If the USS successfully plans Flight 2 or otherwise fails to indicate a conflict, this check will fail.

#### Failure check
All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept Flight 2. If the USS indicates that the injection attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../requirements/interuss/automated_testing/flight_planning.md)**.

### [Validate high-priority Flight 2 not shared test step](../validate_not_shared_operational_intent.md)

### [Restore virtual USS availability at DSS test step](../set_uss_available.md)


## Plan Flight 2 in conflict with contingent operational intent managed by down USS test case
This test case aims at testing requirement **[astm.f3548.v21.SCD0010](../../../../requirements/astm/f3548/v21.md)**.

### Virtual USS transitions to Contingent conflicting operational intent test step
The USS qualifier, acting as a virtual USS, transitions to Contingent the operational intent previously created at the DSS with a non-working base URL.
The objective is to make the later request by the tested USS to retrieve operational intent details to fail.

#### Operational intent successfully transitioned to Contingent check
If the transition of the operational intent reference at the DSS fails, this check fails per **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### [Declare virtual USS as down at DSS test step](../set_uss_down.md)

### Tested USS attempts to plan high-priority Flight 2 test step
The high-priority Flight 2 of the tested USS conflicts with the operational intent of the virtual USS.
However, since:
- the virtual USS is declared as down at the DSS,
- it does not respond for operational intent details, and
- the conflicting operational intent is in the 'Contingent' state,
- the local regulation does not allow for equal priority conflicts at the highest priority level,
The tested USS should evaluate the conflicting operational intent as having the highest priority status allowed by the local regulation.
As such, the tested USS should reject the planning of Flight 2.

#### Incorrectly planned check
All flight intent data provided is correct and the USS should have rejected properly the planning per **[astm.f3548.v21.SCD0010](../../../../requirements/astm/f3548/v21.md)**.
If the USS indicates that the injection attempt failed, this check will fail.
If the USS successfully plans Flight 2 or otherwise fails to indicate a conflict, this check will fail.

#### Failure check
All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to reject or accept Flight 2. If the USS indicates that the injection attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../requirements/interuss/automated_testing/flight_planning.md)**.

### [Validate high-priority Flight 2 not shared test step](../validate_not_shared_operational_intent.md)


## Cleanup
### Availability of virtual USS restored check
**[astm.f3548.v21.DSS0100](../../../../requirements/astm/f3548/v21.md)**

### Successful flight deletion check
Delete flights injected at USS through the flight planning interface.
**[interuss.automated_testing.flight_planning.DeleteFlightSuccess](../../../../requirements/interuss/automated_testing/flight_planning.md)**

### Successful operational intents cleanup check
Delete operational intents created at DSS by virtual USS.
If the search for own operational intents or their deletion fail, this check fails per **[astm.f3548.v21.DSS0005](../../../../requirements/astm/f3548/v21.md)**.
