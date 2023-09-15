# ASTM NetRID DSS: Simple ISA test scenario

## Overview

Perform basic operations on a single DSS instance to create an ISA and query it during its time of applicability and
after its time of applicability.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the ISA ID for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing an ISA to be created.

## Setup test case

### Ensure clean workspace test step

This scenario creates an ISA with a known ID.  This step ensures that ISA does not exist before the start of the main
part of the test.

#### Successful ISA query check

**[astm.f3411.v22a.DSS0030](../../../../../requirements/astm/f3411/v22a.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

#### Removed pre-existing ISA check

If an ISA with the intended ID is already present in the DSS, it needs to be removed before proceeding with the test.  If that ISA cannot be deleted, then the **[astm.f3411.v22a.DSS0030](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Notified subscriber check

When a pre-existing ISA needs to be deleted to ensure a clean workspace, any subscribers to ISAs in that area must be notified (as specified by the DSS).  If a notification cannot be delivered, then the **[astm.f3411.v22a.NET0710](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the POST ISAs endpoint isn't met.

## Create and check ISA test case

### [Create ISA test step](test_steps/put_isa.md)

This step attempts to create at the DSS the ISA provided as resource.

### Get ISA by ID test step

This step attempts to retrieve at the DSS the ISA just created.

#### Successful ISA query check

If the ISA cannot be queried, the GET ISA DSS endpoint in **[astm.f3411.v22a.DSS0030](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

The DSS returns the ID of the ISA in the response body.  If this ID does not match the ID in the resource path, **[astm.f3411.v22a.DSS0030](../../../../../requirements/astm/f3411/v22a.md)** was not implemented correctly and this check will fail.

#### ISA version match check

The DSS returns the version of the ISA in the response body.  If this version does not match the version that was returned after creation, and that no modification of the ISA occurred in the meantime, **[astm.f3411.v22a.DSS0030](../../../../../requirements/astm/f3411/v22a.md)** was not implemented correctly and this check will fail.


## Update and search ISA test case

## Delete ISA test case

## Cleanup

The cleanup phase of this test scenario attempts to remove the ISA if the test ended prematurely.

### Successful ISA query check

**[astm.f3411.v22a.DSS0030](../../../../../requirements/astm/f3411/v22a.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

### Removed pre-existing ISA check

If an ISA with the intended ID is still present in the DSS, it needs to be removed before exiting the test.  If that ISA cannot be deleted, then the **[astm.f3411.v22a.DSS0030](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

### Notified subscriber check

When an ISA is deleted, subscribers must be notified.  If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v22a.NET0730](../../../../../requirements/astm/f3411/v22a.md)**.
