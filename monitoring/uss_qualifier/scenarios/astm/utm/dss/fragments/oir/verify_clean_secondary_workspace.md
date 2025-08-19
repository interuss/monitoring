# Verify secondary DSS contains no OIRs with a test ID test step fragment

Ensures that a secondary DSS is ready to be used for testing by confirming that no OIR bearing an ID used for testing exists on it.

## 🛑 Operational intent references can be queried by ID check

If an existing operational intent reference cannot directly be queried by its ID, or if for a non-existing one the DSS replies with a status code different than 404,
the DSS implementation is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Operational intent reference with test ID does not exist check

If an OIR that was deleted from the primary DSS can still be found on a secondary DSS, either one of them may be improperly pooled
and in violation of **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.


