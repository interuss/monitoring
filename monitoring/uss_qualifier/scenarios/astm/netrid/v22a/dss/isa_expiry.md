# ASTM NetRID DSS: ISA Expiry test scenario

## Overview

Perform basic operations on a single DSS instance in order to verify that it handles ISA expiry correctly.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the ISA ID for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing an ISA to be created.

## Setup test case

### [Ensure clean workspace test step](test_steps/clean_workspace.md)

This scenario creates an ISA with a known ID. This step ensures that the ISA does not exist when the main part of the test starts.

## ISA Expiry test case

This test case creates an ISA with a short lifetime and verifies that it is not returned in search results after it expires.

### ISA Expiry test step

#### Create short-lived ISA check

Not allowing an ISA to be created violates **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**

#### An expired ISA can be queried by its ID check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires that
an ISA be returned in all cases when it is queried directly, even if it expired.

#### Expired ISAs are not part of search results check

**[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires
that ISAs that are in the searched area but have expired should not be returned.

## Cleanup

The cleanup phase of this test scenario attempts to remove the ISA if the test ended prematurely.

### Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

### Removed pre-existing ISA check

If an ISA with the intended ID is still present in the DSS, it needs to be removed before exiting the test. If that ISA cannot be deleted, then the **[astm.f3411.v22a.DSS0030](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

### Notified subscriber check

When an ISA is deleted, subscribers must be notified. If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v22a.NET0730](../../../../../requirements/astm/f3411/v22a.md)**.
