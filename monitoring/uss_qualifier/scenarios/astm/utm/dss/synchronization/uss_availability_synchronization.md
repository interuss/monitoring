# ASTM SCD DSS: USS Availability Synchronization test scenario

## Overview

Verifies that all CRUD operations for USS availabilities on a given DSS instance
are properly propagated to every other DSS instance participating in the deployment.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which USS availabilities are created, modified and deleted.

### other_instances

[`DSSInstancesResource`](../../../../../resources/astm/f3548/v21/dss.py) pointing to the DSS instances used to confirm that USS availabilities are properly propagated.

### client_identity

[`ClientIdentityResource`](../../../../../resources/communications/client_identity.py) to be used for this scenario: it contains the identifier of the USS
for which availabilities will be updated.

## Setup test case

For the setup of this test case, the scenario ensures that the availability for the USS specified in the `client_identity` resource
is `Unknown`, which is the default expected state when nothing else is known.

### Ensure test USS has Unknown availability test step

This step ensures that the scenario starts from a state where the USS availability is `Unknown`.

#### 🛑 USS Availability can be requested check

If, when queried for the availability of a USS using valid credentials, the DSS does not return a valid 200 response,
it is in violation of the OpenAPI spec referenced by **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 USS Availability can be set to Unknown check

A valid request to set the availability of a USS to `Unknown` should be accepted by the DSS,
otherwise it is failing to implement the OpenAPI spec referenced by **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

#### [Consistent availability](../fragments/availability/sync.md)

## USS Availability synchronization test case

Checks that updates to a USS availability on one DSS instance are properly propagated to every other DSS instance in the deployment.

Ensures that this is true for every possible availability state.

### Update USS availability on primary DSS to Normal test step

#### [Availability can be updated](../fragments/availability/update.md)

### Check Normal USS availability broadcast test step

#### [Availability can be read](../fragments/availability/read.md)

#### [Consistent availability](../fragments/availability/sync.md)

### Update USS Availability on primary DSS to Down test step

#### [Availability can be updated](../fragments/availability/update.md)

### Check Down USS availability broadcast test step

#### [Availability can be read](../fragments/availability/read.md)

#### [Consistent availability](../fragments/availability/sync.md)

### Update USS availability on primary DSS to Unknown test step

#### [Availability can be updated](../fragments/availability/update.md)

### Check Unknown USS availability broadcast test step

#### [Availability can be read](../fragments/availability/read.md)

#### [Consistent availability](../fragments/availability/sync.md)

## Unknown USS state is reported as Unknown test case

Checks that if queried for a USS it does not know about, any DSS will return an `Unknown` availability.

### Query all DSS instances with an unknown USS identifier test step

This test step requests the availability for a USS identifier that is not known to any DSS instance, and expects
to receive an `Unknown` availability along with an unset version. This should be true for every DSS that is part of the same deployment.

#### [Request availability](../fragments/availability/read.md)

#### 🛑 Main DSS instance reports Unknown availability check

If the primary DSS instance does not return an `Unknown` availability for a USS identifier that has not received any updates,
it is in violation of the OpenAPI spec referenced by **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Availability version for an unknown USS should be empty check

If the primary DSS instance reports a non-empty version for the availability of an USS identifier that should not be known to the DSS,
it is in violation of the OpenAPI spec referenced by **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

#### [Consistent availability](../fragments/availability/sync.md)

## Cleanup

### ⚠️ USS Availability can be requested check

If, when queried for the availability of a USS using valid credentials, the DSS does not return a valid 200 response,
it is in violation of the OpenAPI spec referenced by **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

### ⚠️ USS Availability can be set to Unknown check

A valid request to set the availability of a USS to `Unknown` should be accepted by the DSS,
otherwise it is failing to implement the OpenAPI spec referenced by **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.
