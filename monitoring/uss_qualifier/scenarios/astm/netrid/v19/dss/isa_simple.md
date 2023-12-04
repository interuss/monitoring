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

### problematically_big_area

[`VerticesResource`](../../../../../resources/vertices.py) describing an area designed to be too big to be accepted by the DSS.

## Setup test case

### [Ensure clean workspace test step](test_steps/clean_workspace.md)

This scenario creates an ISA with a known ID.  This step ensures that ISA does not exist before the start of the main
part of the test.

## Create and check ISA test case

### [Create ISA test step](test_steps/put_isa.md)

This step attempts to query the configured DSS with the ISA provided as a resource.

#### ISA created check

If the ISA cannot be created, the PUT DSS endpoint in **[astm.f3411.v19.DSS0030,a](../../../../../requirements/astm/f3411/v19.md)** is likely not implemented correctly.

### Get ISA by ID test step

This step attempts to retrieve the previously created ISA from the DSS.

#### Successful ISA query check

If the ISA cannot be queried, the GET ISA DSS endpoint in **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** is likely not implemented correctly.

The DSS returns the ID of the ISA in the response body.  If this ID does not match the ID in the resource path, **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

#### ISA version match check

The DSS returns the version of the ISA in the response body.  If this version does not match the version that was returned after creation, and that no modification of the ISA occurred in the meantime, **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

## Update and search ISA test case

### [Update ISA test step](test_steps/put_isa.md)

This step attempts to update the configured DSS with the ISA provided as a resource, with a slightly different end time.

#### ISA updated check

If the ISA cannot be updated, the PUT DSS endpoint in **[astm.f3411.v19.DSS0030,a](../../../../../requirements/astm/f3411/v19.md)** is likely not implemented correctly.

### Get ISA by ID test step

This step attempts to retrieve at the DSS the ISA just updated.

#### Successful ISA query check

If the ISA cannot be queried, the GET ISA DSS endpoint in **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** is likely not implemented correctly.

The DSS returns the ID of the ISA in the response body.  If this ID does not match the ID in the resource path, **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

#### ISA version match check

The DSS returns the version of the ISA in the response body.  If this version does not match the version that was returned after update, and that no modification of the ISA occurred in the meantime, **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

### [Search by earliest time (included) test step](test_steps/search_isas.md)

This step attempts an ISA search at the DSS with the area of the ISA resource and an earliest time that overlaps with the resource ISA.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful.  If the request is not successful, this check will fail per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### ISA returned by search check

The ISA search parameters cover the resource ISA, as such the resource ISA that exists at the DSS should be returned by the search.  If it is not returned, this check will fail.

### [Search by earliest time (excluded) test step](test_steps/search_isas.md)

This step attempts an ISA search at the DSS with the area of the ISA resource and an earliest time that does not overlap with the resource ISA.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful.  If the request is not successful, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### ISA not returned by search check

The ISA search are parameter cover the resource ISA but the earliest time does not, as such the resource ISA that exists at the DSS should not be returned by the search.  If it is returned, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### [Search by latest time (included) test step](test_steps/search_isas.md)

This step attempts an ISA search at the DSS with the area of the ISA resource and a latest time that overlaps with the resource ISA.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful.  If the request is not successful, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### ISA returned by search check

The ISA search parameters cover the resource ISA, as such the resource ISA that exists at the DSS should be returned by the search.  If it is not returned, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### [Search by latest time (excluded) test step](test_steps/search_isas.md)

This step attempts an ISA search at the DSS with the area of the ISA resource and a latest time that does not overlap with the resource ISA.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful.  If the request is not successful, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### ISA not returned by search check

The ISA search are parameter cover the resource ISA but the latest time does not, as such the resource ISA that exists at the DSS should not be returned by the search.  If it is returned, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### [Search by area only test step](test_steps/search_isas.md)

This step attempts an ISA search at the DSS with only the area of the ISA resource.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful.  If the request is not successful, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### ISA returned by search check

The ISA search parameters cover the resource ISA, as such the resource ISA that exists at the DSS should be returned by the search.  If it is not returned, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### Search with invalid params test step

This step attempts an ISA search at the DSS with an empty search area.

#### Search request rejected check

The search request contained invalid parameters (empty search area), as such the DSS should reject it with a 400 HTTP code.  If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### Search by huge area test step

This step attempts an ISA search at the DSS with a too large search area.

#### Search request rejected check

The search request contained invalid parameters (too large search area), as such the DSS should reject it with a 413 HTTP code.  If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### Search ISA with loop test step

This step attempts an ISA search at the DSS with a polygon defining the area that forms a loop.

#### Search request rejected check

The search request contained invalid parameters (area polygon is a loop, which is not allowed), as such the DSS should reject it with a 400 HTTP code.  If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

## Delete ISA test case

### Delete with wrong version test step

This step attempts an ISA deletion with a wrong version.

#### Delete request rejected check

The deletion request contained invalid parameters (wrong version), as such the DSS should reject it with a 409 HTTP code.  If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as per **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)**.

### Delete with empty version test step

This step attempts an ISA deletion with an empty version.

#### Delete request rejected check

The deletion request contained invalid parameters (empty version), as such the DSS should reject it with a 400 HTTP code.  If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as per **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)**.

### [Delete ISA test step](test_steps/delete_isa.md)

This step attempts an ISA deletion at the DSS.

#### ISA deleted check

If the ISA cannot be deleted, the PUT DSS endpoint in **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)** is likely not implemented correctly.

### Get deleted ISA by ID test step

This step attempts to retrieve at the DSS the ISA just deleted.

#### ISA not found check

The ISA fetch request was about a deleted ISA, as such the DSS should reject it with a 404 HTTP code.  If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as per **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### [Search ISA test step](test_steps/search_isas.md)

This step attempts an ISA search at the DSS with only the area of the ISA resource. Since it has just been deleted, the ISA should not be returned.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful.  If the request is not successful, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### ISA not returned by search check

The ISA search are parameter cover the resource ISA, but it has been previously deleted, as such the ISA should not be returned by the search.  If it is returned, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

## Cleanup

The cleanup phase of this test scenario attempts to remove the ISA if the test ended prematurely.

### Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

### Removed pre-existing ISA check

If an ISA with the intended ID is still present in the DSS, it needs to be removed before exiting the test. If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

### Notified subscriber check

When an ISA is deleted, subscribers must be notified. If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v19.NET0730](../../../../../requirements/astm/f3411/v19.md)**.
