# Search constraint reference test step fragment

This test step fragment validates that known constraint references can be searched for, and that the returned content is as expected.

## [Verify search query succeeds](./search_query.md)

## [Validate response format](./search_format.md)

## 🛑 Expected constraint reference is in search results check

If the existing constraint reference is not returned in a search that covers the area it was created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,4](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Search constraint reference response content is correct check

A successful constraint reference search query is expected to return a body, the content of which reflects any constraint reference present in the searched area.
This includes the previously created constraint reference, which should accurately represent the constraint reference as it was requested. If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,4](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
