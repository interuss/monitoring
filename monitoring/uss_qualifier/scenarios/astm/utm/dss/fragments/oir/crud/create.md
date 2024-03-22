# Create operational intent reference test step fragment

This test step fragment validates that operational intent references can be created

## 🛑 Create operational intent reference query succeeds check

As per **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**, the DSS API must allow callers to create an operational intent reference with either one or both of the
start and end time missing, provided all the required parameters are valid.

## [Response Format](./create_format.md)

Check response format

## 🛑 Create operational intent reference response content is correct check

A successful operational intent reference creation query is expected to return a body, the content of which reflects the created operational intent reference.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
