# USS Availability Read test step fragment

This fragment contains the steps for the USS Availability synchronization scenario
where we confirm that a USS availability can be correctly read from a DSS instance

## 🛑 USS Availability can be requested check

If, when queried for the availability of a USS using valid credentials, the DSS does not return a valid 200 response,
it is in violation of the OpenAPI specification referenced by **[astm.f3548.v21.DSS0100,1](../../../../../../requirements/astm/f3548/v21.md)**.
