# USS Availability Cleanup test step fragment

This fragment contains the cleanup steps for the USS Availability synchronization scenario.

## 🛑 USS Availability can be requested check

If, when queried for the availability of a USS using valid credentials, the DSS does not return a valid 200 response,
it is in violation of the OpenAPI spec referenced by DSS0005.

TODO unclear which requirement to point to: DSS0005,[1-5] do not cover this endpoint. DSS0210,A2-7-2,6 is about synchronization

## 🛑 USS Availability can be set to Unknown check

A valid request to set the availability of a USS to `Unknown` should be accepted by the DSS, otherwise it is failing to implement the OpenAPI spec referenced by DSS0005.
