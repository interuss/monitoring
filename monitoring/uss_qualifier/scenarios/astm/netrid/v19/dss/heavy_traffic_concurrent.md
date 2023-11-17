# ASTM NetRID DSS: Concurrent Requests test scenario

## Overview

Create, query and delete ISAs on the DSS, concurrently.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the ISA ID for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing the ISAs to be created. All created ISAs use the same parameters.

## Setup test case

### [Ensure clean workspace test step](test_steps/clean_workspace.md)

This scenario creates ISA's with known IDs. This step ensures that no ISA with a known ID is present in the DSS before proceeding with the test.

## Concurrent Requests test case

This test case will:

1. Create ISAs concurrently
2. Query each ISA individually, but concurrently
3. Search for all ISAs in the area of the created ISAs (using a single request)
4. Delete the ISAs concurrently
5. Query each ISA individually, but concurrently
6. Search for all ISAs in the area of the deleted ISAs (using a single request)

### [Create ISA concurrently test step](test_steps/put_isa.md)

This step attempts to concurrently create multiple ISAs, as specified in this scenario's resource, at the configured DSS.

#### Concurrent ISAs creation check

If any of the concurrent ISA creation requests fail or leads to the creation of an incorrect ISA, the PUT DSS endpoint in **[astm.f3411.v19.DSS0030,a](../../../../../requirements/astm/f3411/v19.md)** is likely not implemented correctly.

### [Get ISAs concurrently test step](test_steps/get_isa.md)

This step attempts to concurrently retrieve the previously created ISAs from the DSS.

#### Successful Concurrent ISA query check

If any of the ISAs cannot be queried, the GET ISA DSS endpoint in **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** is likely not implemented correctly.

### [Search Available ISAs test step](test_steps/search_isas.md)

This test step searches the area in which the ISAs were concurrently created, and expects to find all of them.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful. If the request is not successful, this check will fail per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### Correct ISAs returned by search check

The ISA search parameters cover the resource ISA, as such the resource ISA that exists at the DSS should be returned by the search. If it is not returned, this check will fail.

### [Delete ISAs concurrently test step](test_steps/delete_isa.md)

This step attempts to concurrently delete the earlier created ISAs.

#### ISAs deletion query success check

If an ISA cannot be deleted, the PUT DSS endpoint in **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)** is likely not implemented correctly.

### Access Deleted ISAs test step

This step attempts to concurrently access the previously deleted ISAs from the DSS.

#### ISAs not found check

The ISA fetch request was about a deleted ISA, as such the DSS should reject it with a 404 HTTP code. If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as per **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### [Search Deleted ISAs test step](test_steps/search_isas.md)

This step issues a search for active ISAs in the area of the previously deleted ISAs from the DSS.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful. If the request is not successful, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### ISAs not returned by search check

The ISA search area parameter cover the resource ISA, but it has been previously deleted, as such the ISA should not be returned by the search. If it is returned, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

## Cleanup

The cleanup phase of this test scenario attempts to remove any created ISA if the test ended prematurely.

### Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

### Removed pre-existing ISA check

If an ISA with the intended ID is still present in the DSS, it needs to be removed before exiting the test. If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

### Notified subscriber check

When an ISA is deleted, subscribers must be notified. If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v19.NET0730](../../../../../requirements/astm/f3411/v19.md)**.
