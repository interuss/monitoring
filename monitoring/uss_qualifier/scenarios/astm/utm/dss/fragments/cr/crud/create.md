# Create constraint reference test step fragment

This test step fragment validates that:
 - a query to create a constraint reference with valid parameters succeeds
 - the response to the query conforms to the OpenAPI specification
 - the content of the response reflects the created constraint reference

## [Verify query Success](./create_query.md)

## [Validate Response Format](./create_format.md)

## 🛑 Create constraint reference response content is correct check

A successful constraint reference creation query is expected to return a body, the content of which reflects the created constraint reference.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
