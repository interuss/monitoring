# ASTM NetRID DSS: Token Validation test scenario

## Overview

Checks that the DSS properly validates the provided client token on all its endpoints.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the ISA ID for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing an ISA to be created.

## Setup test case

### [Ensure clean workspace test step](test_steps/clean_workspace.md)

This scenario creates an ISA with a known ID.  This step ensures that ISA does not exist before the start of the main
part of the test.

## Token validation test case

### [Token validation test step](test_steps/put_isa.md)

This step attempts to create and read ISAs by providing both the correct and incorrect scopes, omitting the token or providing an invalid one,
and expects the DSS to properly behave in each case.

#### Read scope cannot create an ISA check

If an ISA can be created with a scope that does not provide write permission, the DSS is in violation of **[astm.f3411.v19.DSS0030,a](../../../../../requirements/astm/f3411/v19.md)**.

#### Missing token prevents creating an ISA check

If an ISA can be created without a token being present in the request, the DSS is in violation of **[astm.f3411.v19.DSS0010](../../../../../requirements/astm/f3411/v19.md)**.

#### Fake token prevents creating an ISA check

If an ISA can be created with an incorrect token in the request, the DSS is in violation of **[astm.f3411.v19.DSS0030,a](../../../../../requirements/astm/f3411/v19.md)**.

#### Correct token and scope can create ISA check

If the ISA cannot be created when the proper credentials are presented,
the PUT DSS endpoint in **[astm.f3411.v19.DSS0030,a](../../../../../requirements/astm/f3411/v19.md)** is likely not implemented correctly.

#### Missing token prevents reading an ISA check

If the ISA that was created can be accessed without a token being present in the request,
the DSS is in violation of **[astm.f3411.v19.DSS0010](../../../../../requirements/astm/f3411/v19.md)**

#### Fake token prevents reading an ISA check

If the ISA that was created can be accessed using a token with an invalid signature,
the DSS is in violation of **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)**

#### Read scope cannot mutate an ISA check

If the existing ISA can be mutated by using a read-only scope, the DSS is in violation of **[astm.f3411.v19.DSS0030,a](../../../../../requirements/astm/f3411/v19.md)**

#### Missing token prevents mutating an ISA check

If the existing ISA can be mutated without a token being provided, the DSS is in violation of **[astm.f3411.v19.DSS0010](../../../../../requirements/astm/f3411/v19.md)**

#### Proper token is allowed to search for ISAs check

If a valid token is presented as part of the search request, and the search parameters are valid, the DSS must return a 200 response, or be in violation of **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### Fake token cannot mutate an ISA check

If the existing ISA can be mutated by using an invalid token, the DSS is in violation of **[astm.f3411.v19.DSS0030,a](../../../../../requirements/astm/f3411/v19.md)**

#### Fake token cannot search for ISAs check

If the DSS accepts search queries with an invalid token, it is in violation of **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### Missing token cannot search for ISAs check

If the DSS accepts search queries without a token, it is in violation of **[astm.f3411.v19.DSS0010](../../../../../requirements/astm/f3411/v19.md)**.

#### Read scope cannot delete an ISA check

If the existing ISA can be deleted by using a read-only scope, the DSS is in violation of **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)**

#### Missing token prevents ISA deletion check

If the existing ISA can be deleted without a token being provided, the DSS is in violation of **[astm.f3411.v19.DSS0010](../../../../../requirements/astm/f3411/v19.md)**

#### Fake token cannot delete an ISA check

If the existing ISA can be deleted by using an invalid token, the DSS is in violation of **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)**

#### Correct token and scope can delete ISA check

If the existing ISA cannot be deleted when the proper credentials are presented, the DSS is in violation of **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)**

#### Notified subscriber check

When an ISA is deleted, subscribers must be notified. If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v19.NET0730](../../../../../requirements/astm/f3411/v19.md)**.

## Cleanup

The cleanup phase of this test scenario attempts to remove the ISA if the test ended prematurely.

### Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

### Removed pre-existing ISA check

If an ISA with the intended ID is still present in the DSS, it needs to be removed before exiting the test. If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

### Notified subscriber check

When an ISA is deleted, subscribers must be notified. If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v19.NET0730](../../../../../requirements/astm/f3411/v19.md)**.
