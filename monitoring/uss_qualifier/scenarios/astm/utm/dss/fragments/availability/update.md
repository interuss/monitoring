# USS Availability Read test step fragment

This fragment contains the steps for the USS Availability synchronization scenario
where we confirm that a USS availability can be correctly read from a DSS instance

## 🛑 USS Availability can be updated check

If, when presented with a valid query to update the availability state of a USS, a DSS
responds with anything else than a 200 OK response, it is in violation of the OpenAPI specification referenced by **[astm.f3548.v21.DSS0100,1](../../../../../../requirements/astm/f3548/v21.md)**.
