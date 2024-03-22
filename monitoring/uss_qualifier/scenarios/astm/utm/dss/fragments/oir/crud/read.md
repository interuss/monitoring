# Read operational intent reference test step fragment

This test step fragment validates that operational intent references can be read

## 🛑 Get operational intent reference by ID check

If an operational intent reference cannot be queried using its ID, the DSS is failing to meet **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Get operational intent reference response format conforms to spec check

The response to a successful get operational intent reference query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.
