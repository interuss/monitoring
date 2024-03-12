# Search operational intent reference test step fragment

This test step fragment validates that operational intent references can be searched for

## [Search query succeeds](./search_query.md)

Check query succeeds.

## 🛑 Search operational intent reference response format conforms to spec check

The response to a successful operational intent reference search query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Created operational intent reference is in search results check

If the existing operational intent reference is not returned in a search that covers the area it was created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,2](../../../../../../../requirements/astm/f3548/v21.md)**.
