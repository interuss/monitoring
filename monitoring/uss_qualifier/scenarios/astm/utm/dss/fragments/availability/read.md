# USS Availability Read test step fragment

This fragment contains the steps for the USS Availability synchronization scenario
where we confirm that a USS availability can be correctly read from a DSS instance

## 🛑 USS Availability can be requested check

If, when queried for the availability of a USS using valid credentials, the DSS does not return a valid 200 response,
it is in violation of the OpenAPI spec referenced by DSS0005.

TODO unclear which requirement to point to: DSS0005,[1-5] do not cover this endpoint. DSS0210,A2-7-2,6 is about synchronization.
Should we add a 'synthetic' requirement based on the OpenAPI spec, as it was done for the NetRID requirements?

