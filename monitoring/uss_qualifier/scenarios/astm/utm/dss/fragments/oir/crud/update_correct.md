# Update operational intent reference test step fragment

This test step fragment validates that operational intent references can be updated.

## [Update query succeeds](./update_query.md)

Check query succeeds.

## [Response Format](./update_format.md)

Check response format

## 🛑 Mutate operational intent reference response content is correct check

A successful operational intent reference mutation query is expected to return a well-defined body, the content of which reflects the updated operational intent reference.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
