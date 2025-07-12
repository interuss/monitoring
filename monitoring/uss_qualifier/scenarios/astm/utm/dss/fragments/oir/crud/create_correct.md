# Create operational intent reference test step fragment

This test step fragment validates that:
 - a query to create an operational intent reference with valid parameters succeeds
 - the response to the query conforms to the OpenAPI specification
 - the content of the response reflects the created operational intent reference

## [Query Success](./create_query.md)

Check query succeeds

## [Response Format](./create_format.md)

Check response format

## 🛑 Create operational intent reference response content is correct check

A successful operational intent reference creation query is expected to return a body, the content of which reflects the created operational intent reference.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.

## [Validate created OIR fields](../validate/correctness.md)
