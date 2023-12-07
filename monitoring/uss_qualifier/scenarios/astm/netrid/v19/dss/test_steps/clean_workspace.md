# Ensure clean workspace test step fragment

This page describes the content of a common test step that ensures a clean workspace for testing interactions with a DSS

## Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

## Removed pre-existing ISA check

If an ISA with the intended ID is already present in the DSS, it needs to be removed before proceeding with the test.  If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030,d](../../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

## Notified subscriber check

When a pre-existing ISA needs to be deleted to ensure a clean workspace, any subscribers to ISAs in that area must be notified (as specified by the DSS).  If a notification cannot be delivered, then the **[astm.f3411.v19.NET0730](../../../../../../requirements/astm/f3411/v19.md)** requirement to implement the POST ISAs endpoint isn't met.

## Successful subscription search query check

**[astm.f3411.v19.DSS0030,f](../../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint to allow callers to retrieve the subscriptions they created.

## Subscription can be queried by ID check

If the DSS cannot be queried for the existing test ID, the DSS is likely not implementing **[astm.f3411.v19.DSS0030,e](../../../../../../requirements/astm/f3411/v19.md)** correctly.

## Subscription can be deleted check

**[astm.f3411.v19.DSS0030,d](../../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint to allow callers to delete subscriptions they created.
