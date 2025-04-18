# Delete operational intent reference response format test step fragment

This test step fragment validates that an operational intent references deletion returns a body in the correct format and with the correct content.

## [Query Success](./delete_query.md)

Check query succeeds

## 🛑 Delete operational intent reference response format conforms to spec check

The response to a successful operational intent reference deletion query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Delete operational intent reference response content is correct check

A successful operational intent reference deletion query is expected to return a body, the content of which reflects the operational intent reference at the moment of deletion.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
