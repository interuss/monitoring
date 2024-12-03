# ASTM F3548-21 UTM DSS Operational Intent Reference State Transitions test scenario

## Overview

This scenario ensures that a DSS will only let the owner of an operational intent reference modify it.

## Resources

### flight_intents

A `resources.flight_planning.FlightIntentsResource` containing the flight intents to be used in this scenario:

This scenario expects to find at least one flight intent in this resource. It will use its extents to create and mutate an operational intent reference,
but ignore any specified states, as this scenario will iterate over all allowed states.

### dss

A `resources.astm.f3548.v21.DSSInstanceResource` pointing to the DSS instance to test for this scenario.

### id_generator

A `resources.interuss.IDGeneratorResource` that will be used to generate the IDs of the operational intent references created in this scenario.

## Setup test case

Makes sure that the DSS is in a clean and expected state before running the test, and that the passed resources work as required.

### Ensure clean workspace test step

#### [Clean any existing OIRs with known test IDs](clean_workspace_op_intents.md)

#### [No OIR exists](fragments/oir/cleanup_required.md)

## Attempt unauthorized state creation test case

This test case attempts to create an operational intent reference with a state that would require the `utm.conformance_monitoring_sa` scope while only using
the `utm.strategic_coordination` scope.

### Attempt direct creation with unauthorized state test step

This test step attempts to directly create an operational intent reference with a state that is not allowable.

The creation of such an entity is expected to fail for two reasons:

 - the initial state of any OIR must be `Accepted`
 - Without the `utm.conformance_monitoring_sa`, a client is not allowed to request an Off-nominal state.

#### 🛑 Direct Nonconforming state creation is forbidden check

If the DSS allows a client with the `utm.strategic_coordination` scope to create an operational intent reference in the `Nonconforming` state,
it is in violation of **[astm.f3548.v21.SCD0100](../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Direct Contingent state creation is forbidden check

If the DSS allows a client with the `utm.strategic_coordination` scope to create an operational intent reference in the `Contingent` state,
it is in violation of **[astm.f3548.v21.SCD0100](../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Attempt unauthorized state transitions test case

This test case attempts to transition an existing operational intent reference to a state that would require the `utm.conformance_monitoring_sa` scope while only using
the `utm.strategic_coordination` scope.

### Create an Accepted OIR test step

This step sets up an operational intent reference in the `Accepted` state.

#### 🛑 Creation of an Accepted OIR is allowed check

If the DSS does not allow a client with the `utm.strategic_coordination` scope to create an operational intent reference in the `Accepted` state,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Attempt transition of an accepted operational intent reference to an unauthorized state test step

This test step attempts to transition an existing operational intent reference to a state it should not be allowed to when using the ``utm.strategic_coordination` scope.

#### 🛑 Transition from Accepted to Nonconforming is forbidden check

If the DSS allows a client with the `utm.strategic_coordination` scope to transition an operational intent reference from the `Accepted` state to the `Nonconforming` state,
it is in violation of **[astm.f3548.v21.SCD0100](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Transition from Accepted to Contingent is forbidden check

If the DSS allows a client with the `utm.strategic_coordination` scope to transition an operational intent reference from the `Accepted` state to the `Contingent` state,
it is in violation of **[astm.f3548.v21.SCD0100](../../../../requirements/astm/f3548/v21.md)**.

### Transition the OIR to Activated test step

This step transitions the operational intent reference to the `Activated` state.

#### 🛑 Transition from Accepted to Activated is allowed check

If the DSS does not allow a client with the `utm.strategic_coordination` scope to transition an operational intent reference from the `Accepted` state to the `Activated` state,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Attempt transition of an activated operational intent reference to an unauthorized state test step

#### 🛑 Transition from Activated to Nonconforming is forbidden check

If the DSS allows a client with the `utm.strategic_coordination` scope to transition an operational intent reference from the `Activated` state to the `Nonconforming` state,
it is in violation of **[astm.f3548.v21.SCD0100](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Transition from Activated to Contingent is forbidden check

If the DSS allows a client with the `utm.strategic_coordination` scope to transition an operational intent reference from the `Activated` state to the `Contingent` state,
it is in violation of **[astm.f3548.v21.SCD0100](../../../../requirements/astm/f3548/v21.md)**.

### Transition the OIR to Ended test step

#### 🛑 Transition from Activated to Ended is allowed check

If the DSS does not allow a client with the `utm.strategic_coordination` scope to transition an operational intent reference from the `Activated` state to the `Ended` state,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Attempt transition of an ended operational intent reference to an unauthorized state test step

#### 🛑 Transition from Ended to Nonconforming is forbidden check

If the DSS allows a client with the `utm.strategic_coordination` scope to transition an operational intent reference from the `Ended` state to the `Nonconforming` state,
it is in violation of **[astm.f3548.v21.SCD0100](../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Transition from Ended to Contingent is forbidden check

If the DSS allows a client with the `utm.strategic_coordination` scope to transition an operational intent reference from the `Ended` state to the `Contingent` state,
it is in violation of **[astm.f3548.v21.SCD0100](../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.


## [Cleanup](clean_workspace_op_intents.md)
