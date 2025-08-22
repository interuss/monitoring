# ASTM Availability DSS: USS Availability Simple test scenario

## Overview

Verifies the behavior of a DSS for simple interactions pertaining to USS availability status.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which entities are created, modified and deleted.

### client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) the client identity with the `utm.availability_arbitration` scope that will be used to report the availability status.

## Update USS availability state test case

### Declare USS as available at DSS test step

#### [Availability can be read](./fragments/availability/read.md)

#### [Availability can be updated](./fragments/availability/update.md)

## Update requires correct version test case

Test DSS behavior when update requests are not providing the required version.

### Attempt update with missing version test step

This step verifies that an existing USS availability status cannot be mutated with a missing version.

#### 🛑 Request to update USS availability status with empty version fails check

If the DSS under test allows the qualifier to update the USS availability status with a request that provided an empty version, it is in violation of **[astm.f3548.v21.DSS0100,1](../../../../requirements/astm/f3548/v21.md)**

### Attempt update with incorrect version test step

This step verifies that an existing OIR cannot be mutated with an incorrect version.

#### 🛑 Request to update USS availability status with incorrect version fails check

If the DSS under test allows the qualifier to update the USS availability status with a request that provided an incorrect version,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**
