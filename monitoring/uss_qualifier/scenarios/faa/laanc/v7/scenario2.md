# FAA LAANC: Overlapping authorizations test scenario

## Overview

This scenario checks:
* User identification and authentication
* Temporally overlapping authorizations exceed allowable spatial distance
* Excessive number of temporally overlapping authorizations
* Update operation (if offered)

*Note that none of this scenario is implemented yet.*

## Resources

## Future resources

*All items in this section should be moved to the "Resources" section once implemented.*

### flight_planner

This FlightPlannerResource provides access to the interface implemented by the USS under test which uss_qualifier can use to emulate a human performing flight planning activities (e.g., "Try to create a flight in the yellow area during this time period using Part 107 rules").

### flight_intents

This FlightIntentsResource must provide the following flight intents:

- `chester_pa_p107`: Yellow Chester, PA flight beginning more than 72 hours in the future with a maximum altitude of 200', under the Part 107 rules (described in Step 4)
- `williamsport_pa_p107`: IPT UASFM (Williamsport, PA) flight over 100 NM away from `chester_pa_p107`, but overlapping in time with `chester_pa_p107` (described in Step 7)
- `chester_pa_p107_2`, `chester_pa_p107_3`, `chester_pa_p107_4`, `chester_pa_p107_5`, `chester_pa_p107_6`: Flights that all overlap `chester_pa_p107` in time and space, but are otherwise valid
- `chester_pa_p107_b`: Same as `chester_pa_p107`, but with a valid change that the user should make to that initial request

### mock_laanc_server

This MockLAANCServerResource provides test-director-level access to the LAANC server in use for the test environment, allowing uss_qualifier to obtain the information for all current authorizations potentially relevant to a specified profile.

## Steps 4-6 for Part 107 test case

### Retrieve pre-existing LAANC authorizations test step

uss_qualifier retrieves all LAANC authorizations possibly relevant to the `chester_pa_p107` flight to reject these pre-existing authorizations as consequences of the flight planned later in this test case.

#### LAANC authorizations obtained successfully check

If the `mock_laanc_server` does not return a valid list of authorizations in the requested area, the provider of this mock server will not have met **[interuss.automated_testing.faa.laanc.v1.laanc_mock.TestDirectorInterface](../../../../requirements/interuss/automated_testing/faa/laanc/v1/laanc_mock.md)**.

### Plan Chester Part 107 flight test step

uss_qualifier instructs the USS to emulate a user attempting to plan the `chester_pa_p107` flight intent.

This is equivalent to "Step 4" plus part of "Step 5" ("Submit the operation to the FAA") in the standard FAA Onboarding Test Procedure.

#### Successful planning check

The requested flight intent does not violate any LAANC rules, so the USS is not properly providing sUAS authorizations as a service to operators if it does not successfully plan the flight (**[faa.laanc.v7.3,1a](../../../../requirements/faa/laanc/v7.md)**).

#### Reference code check

**[faa.laanc.v7.3,4,6b](../../../../requirements/faa/laanc/v7.md)** specifies that the LAANC authorization reference code must be made available to the operator and **[interuss.automated_testing.faa.laanc.v1.uss.IncludeReferenceCode](../../../../requirements/interuss/automated_testing/faa/laanc/v1/uss.md)**

### Retrieve LAANC authorizations test step

uss_qualifier retrieves all LAANC authorizations possibly relevant to the `chester_pa_p017` flight to check for new authorizations likely to be the result of flight planning in the previous step.

#### LAANC authorizations obtained successfully check

If the `mock_laanc_server` does not return a valid list of authorizations in the requested area, the provider of this mock server will not have met **[interuss.automated_testing.faa.laanc.v1.laanc_mock.TestDirectorInterface](../../../../requirements/interuss/automated_testing/faa/laanc/v1/laanc_mock.md)**.

### Evaluate LAANC authorization test step

In this step, uss_qualifier compares the "before" set of LAANC authorizations (perhaps none) with the "after" set of LAANC authorizations to find the LAANC authorization that the USS under test used to fulfill the Part 107 flight planning intent.  That authorization is then examined to ensure correctness given the known flight intent.

This is equivalent to part of "Step 5" ("Record the LAANC Reference Code(s)") and "Step 6" in the standard FAA Onboarding Test Procedure.

#### LAANC authorization created check

The USS should have created a LAANC authorization as a result of planning the flight in the previous step.  If no new, applicable LAANC authorization was found, the USS must not have confirmed a digital response was received from the FAA (**[faa.laanc.v7.3,4,1a](../../../../requirements/faa/laanc/v7.md)**).

If a LAANC authorization was created, however, the USS must have satisfied **[faa.laanc.v7.3,2,1a](../../../../requirements/faa/laanc/v7.md)**.

#### Correct facility check

The facility that should be specified in the LAANC authorization for the `chester_pa_107` flight is PHL.  If this facility is not specified in the authorization, the USS does not satisfy **[faa.laanc.v7.3,4,3b](../../../../requirements/faa/laanc/v7.md)**.

#### Only one grid cell check

If the LAANC authorization involves more than one grid cell, then the USS subdivided the operational volume for a reason outside the enumerated, allowed reasons (**[faa.laanc.v7.3,3,3a](../../../../requirements/faa/laanc/v7.md)**).

#### Correct grid cell check

The PHL UASFM grid cell in which the LAANC authorization for the `chester_pa_p107` flight is XXX.  If this LAANC authorization does not specify this grid cell, or specifies other grid cells, the USS did not apply the appropriate UASFM to the operation (**[faa.laanc.v7.3,3,1a](../../../../requirements/faa/laanc/v7.md)**).

## Step 7 for Part 107 test case

### Plan Williamsport Part 107 flight test step

uss_qualifier instructs the USS to emulate a user attempting to plan the `williamsport_pa_p107` flight intent.

This is equivalent to "Step 7" in the standard FAA Onboarding Test Procedure.

#### Correctly rejected check

The requested flight intent is too far away to co-exist with the previous, simultaneous operation.  If the USS successfully plans this flight, it does not meet **[faa.laanc.v7.3,7d](../../../../requirements/faa/laanc/v7.md)**.

### Retrieve LAANC authorizations test step

uss_qualifier retrieves all LAANC authorizations possibly relevant to the `williamsport_pa_p107` flight to check for new authorizations likely to be the result of flight planning in the previous step.

#### LAANC authorizations obtained successfully check

If the `mock_laanc_server` does not return a valid list of authorizations in the requested area, the provider of this mock server will not have met **[interuss.automated_testing.faa.laanc.v1.laanc_mock.TestDirectorInterface](../../../../requirements/interuss/automated_testing/faa/laanc/v1/laanc_mock.md)**.

#### Authorization incorrectly created check

If the USS indicating planning failure to the user but nonetheless created a LAANC authorization, the USS does not meet **[faa.laanc.v7.3,7d](../../../../requirements/faa/laanc/v7.md)**.  If any new authorizations appeared since just prior to this unsuccessful planning attempt, we can infer that this is the case.

## Step 8 for Part 107 test case

### Plan additional Chester Part 107 flights test step

uss_qualifier instructs the USS to emulate a user attempting to plan the next `chester_pa_p107_<i>` flight intent.

Note that planning may succeed or fail for these flights.

This is equivalent to "Step 8" in the standard FAA Onboarding Test Procedure.

#### Early rejection check

Blocking before the 6th Chester submission is permissible but not required.  If a USS blocks early, it meets **[faa.laanc.v7.3,7e](../../../../requirements/faa/laanc/v7.md)**.

#### Warning message check

**[faa.laanc.v7.3,7e](../../../../requirements/faa/laanc/v7.md)** requires that a USS must display a message to user when new submissions overlap old submissions.  If the flight planning result does not indicate that an advisory accompanies the successful planning result, then the USS does not meet this requirement.

### Retrieve LAANC authorizations test step

uss_qualifier retrieves all LAANC authorizations possibly relevant to the `williamsport_pa_p107` flight to check for new authorizations likely to be the result of flight planning in the previous step.

#### LAANC authorizations obtained successfully check

If the `mock_laanc_server` does not return a valid list of authorizations in the requested area, the provider of this mock server will not have met **[interuss.automated_testing.faa.laanc.v1.laanc_mock.TestDirectorInterface](../../../../requirements/interuss/automated_testing/faa/laanc/v1/laanc_mock.md)**.

#### LAANC authorization created check

If the USS indicated a successfully-planned flight in the previous step, it should have created a LAANC authorization.  If no new, applicable LAANC authorization was found, the USS must not have confirmed a digital response was received from the FAA (**[faa.laanc.v7.3,4,1a](../../../../requirements/faa/laanc/v7.md)**).

#### Authorization incorrectly created check

If the USS indicated a rejected flight in the previous step, it should not have created a LAANC authorization.  If it nonetheless created a LAANC authorization, the USS does not meet **[faa.laanc.v7.3,7d](../../../../requirements/faa/laanc/v7.md)**.  If any new authorizations appeared since just prior to this unsuccessful planning attempt, we can infer that this is the case.

## Step 9 for Part 107 test case

### Plan 6th Chester Part 107 flight test step

uss_qualifier instructs the USS to emulate a user attempting to plan the `chester_pa_p107_6` flight intent.

This is equivalent to "Step 9" in the standard FAA Onboarding Test Procedure.

#### Correctly rejected check

The requested flight intent would cause too many overlapping simultaneous flights.  If the USS successfully plans this flight, it does not meet **[faa.laanc.v7.3,7c](../../../../requirements/faa/laanc/v7.md)**.

### Retrieve LAANC authorizations test step

uss_qualifier retrieves all LAANC authorizations possibly relevant to the `chester_pa_p107_6` flight to check for new authorizations likely to be the result of flight planning in the previous step.

#### LAANC authorizations obtained successfully check

If the `mock_laanc_server` does not return a valid list of authorizations in the requested area, the provider of this mock server will not have met **[interuss.automated_testing.faa.laanc.v1.laanc_mock.TestDirectorInterface](../../../../requirements/interuss/automated_testing/faa/laanc/v1/laanc_mock.md)**.

#### Authorization incorrectly created check

If the USS indicating planning failure to the user but nonetheless created a LAANC authorization, the USS does not meet **[faa.laanc.v7.3,7c](../../../../requirements/faa/laanc/v7.md)**.  If any new authorizations appeared since just prior to this unsuccessful planning attempt, we can infer that this is the case.

## Steps 10-12 for Part 107 test case

### Change Chester Part 107 flight test step

uss_qualifier instructs the USS to emulate a user attempting to change their existing `chester_pa_p107` flight intent to `chester_pa_p107_b`.

This is equivalent to "Step 10" and "Step 11" in the standard FAA Onboarding Test Procedure.

#### Correctly updated check

The requested update operation should be successful.  If the USS does not successfully update the operation, it does not meet **[faa.laanc.v7.3,4,7a](../../../../requirements/faa/laanc/v7.md)**.

### Retrieve LAANC authorizations test step

uss_qualifier retrieves all LAANC authorizations possibly relevant to the `chester_pa_p107_b` flight to check for new authorizations likely to be the result of flight planning in the previous step.

#### LAANC authorizations obtained successfully check

If the `mock_laanc_server` does not return a valid list of authorizations in the requested area, the provider of this mock server will not have met **[interuss.automated_testing.faa.laanc.v1.laanc_mock.TestDirectorInterface](../../../../requirements/interuss/automated_testing/faa/laanc/v1/laanc_mock.md)**.

#### LAANC authorization updated check

The USS should have updated the existing LAANC authorization as a result of updating the flight in the previous step.  If no the existing LAANC authorization was not updated, the USS must not have confirmed a digital response was received from the FAA (**[faa.laanc.v7.3,4,1a](../../../../requirements/faa/laanc/v7.md)**).

If a LAANC authorization was updated, however, the USS must have satisfied **[faa.laanc.v7.3,2,1a](../../../../requirements/faa/laanc/v7.md)**.

#### Correct facility check

The facility that should be specified in the updated LAANC authorization for the `chester_pa_107_b` flight is PHL.  If this facility is not specified in the authorization, the USS does not satisfy **[faa.laanc.v7.3,4,3b](../../../../requirements/faa/laanc/v7.md)**.

#### Only one grid cell check

If the LAANC authorization involves more than one grid cell, then the USS subdivided the operational volume for a reason outside the enumerated, allowed reasons (**[faa.laanc.v7.3,3,3a](../../../../requirements/faa/laanc/v7.md)**).

#### Correct grid cell check

The PHL UASFM grid cell in which the LAANC authorization for the `chester_pa_p107_b` flight is XXX.  If this LAANC authorization does not specify this grid cell, or specifies other grid cells, the USS did not apply the appropriate UASFM to the operation (**[faa.laanc.v7.3,3,1a](../../../../requirements/faa/laanc/v7.md)**).
