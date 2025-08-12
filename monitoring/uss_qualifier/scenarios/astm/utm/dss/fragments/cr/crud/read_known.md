# Read constraint reference test step fragment

This test step fragment validates that a known constraint references can be read, and that its content is as expected.

## [Verify query succeeds](./read_query.md)

## [Validate response format](./read_format.md)

## 🛑 Get constraint reference response content is correct check

A successful constraint reference creation query is expected to return a body, the content of which reflects a constraint reference that was created earlier.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
