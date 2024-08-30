# Read constraint reference test step fragment

This test step fragment validates that constraint references can be read

## [Read query succeeds](./read_query.md)

Check query succeeds.

## [Read response format](./read_format.md)

Check response format

## 🛑 Get constraint reference response content is correct check

A successful constraint reference creation query is expected to return a body, the content of which reflects a constraint reference that was created earlier.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
