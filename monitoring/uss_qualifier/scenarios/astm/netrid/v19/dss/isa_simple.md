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

**[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

#### Removed pre-existing ISA check

If an ISA with the intended ID is already present in the DSS, it needs to be removed before proceeding with the test.  If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Notified subscriber check

When a pre-existing ISA needs to be deleted to ensure a clean workspace, any subscribers to ISAs in that area must be notified (as specified by the DSS).  If a notification cannot be delivered, then the **[astm.f3411.v19.NET0710](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the POST ISAs endpoint isn't met.

## Create and check ISA test case

### Create ISA test step

This step attempts to create at the DSS the ISA provided as resource.

#### ISA created check

If the ISA cannot be created, the PUT DSS endpoint in **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** is likely not implemented correctly.

When the ISA is created, the DSS returns the ID of the ISA in the response body.  If this ID does not match the ID in the resource path, **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** was not implemented correctly and this check will fail.

When the ISA is created, the DSS returns the URL of the ISA in the response body.  If this URL does not match the URL requested, **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** is not implemented correctly and this check will fail.

The ISA creation request specified an exact start time slightly past now, so the DSS should have created an ISA starting at exactly that time.  If the DSS response indicates the ISA start time is not this value, **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** is not implemented correctly and this check will fail.

The ISA creation request specified an exact end time, so the DSS should have created an ISA ending at exactly that time.  If the DSS response indicates the ISA end time is not this value, **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** is not implemented correctly and this check will fail.

Because the ISA version must be used in URLs, it must be URL-safe even though the ASTM standards do not explicitly require this.  If the indicated ISA version is not URL-safe, this check will fail.

The API for **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** specifies an explicit format that the DSS responses must follow.  If the DSS response does not validate against this format, this check will fail.

### Get ISA by ID test step

This step attempts to retrieve at the DSS the ISA just created.

#### Successful ISA query check

If the ISA cannot be queried, the GET ISA DSS endpoint in **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** is likely not implemented correctly.

The DSS returns the ID of the ISA in the response body.  If this ID does not match the ID in the resource path, **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** was not implemented correctly and this check will fail.

#### ISA version match check

The DSS returns the version of the ISA in the response body.  If this version does not match the version that was returned after creation, and that no modification of the ISA occurred in the meantime, **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** was not implemented correctly and this check will fail.


## Update and search ISA test case

## Delete ISA test case

## Cleanup

The cleanup phase of this test scenario attempts to remove the ISA if the test ended prematurely.

### Successful ISA query check

**[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

### Removed pre-existing ISA check

If an ISA with the intended ID is still present in the DSS, it needs to be removed before exiting the test.  If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

### Notified subscriber check

When an ISA is deleted, subscribers must be notified.  If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v19.NET0730](../../../../../requirements/astm/f3411/v19.md)**.
