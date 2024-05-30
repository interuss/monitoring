# Search constraint reference test step fragment

This test step fragment validates that constraint references can be searched for

## [Search query succeeds](./search_query.md)

Check query succeeds.

## 🛑 Search constraint reference response format conforms to spec check

The response to a successful constraint reference search query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Expected constraint reference is in search results check

If the existing constraint reference is not returned in a search that covers the area it was created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,4](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Search constraint reference response content is correct check

A successful constraint reference search query is expected to return a body, the content of which reflects any constraint reference present in the searched are.
This includes the previously created constraint reference, which should accurately represent the constraint reference as it was requested. If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,4](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
