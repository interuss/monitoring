# Update constraint reference test step fragment

This test step fragment validates that constraint references can be updated.

## [Verify update query succeeds](./update_query.md)

## [Validate response format](./update_format.md)

## 🛑 Mutate constraint reference response content is correct check

A successful constraint reference mutation query is expected to return a well-defined body, the content of which reflects the updated constraint reference.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
