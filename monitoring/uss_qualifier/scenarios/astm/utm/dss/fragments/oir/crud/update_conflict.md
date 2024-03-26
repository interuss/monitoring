# Conflict on operational intent reference update test step fragment

This test step fragment validates that requests for operational intent references updates that
don't show that they have been de-conflicted are rejected with the proper error.

## 🛑 Mutate operational intent reference with missing OVN fails check

If the DSS allows the mutation of an operational intent reference that is missing the required OVNs for other entities that exist in its geo-temporal vicinity,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0210,A2-7-2,2b](../../../../../../../requirements/astm/f3548/v21.md)**

## 🛑 Failure response due to conflict has proper format check

The DSS is expected to return a `HTTP 409` error response when the creation of an operational intent reference fails due to a conflict.
This response is expected to conform to the OpenAPI spec that is part of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

Should this not be the case, then the DSS is in violation of the aforementioned requirement.

## 🛑 Failure response due to conflict contains conflicting OIRs check

If the DSS returns a `HTTP 409` error response due to a conflict, and the response body contains a `missing_operational_intents` field,
this field is expected to contain the conflicting OVNs.

If the field exists but does not contain the conflicting OVNs, then the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.
