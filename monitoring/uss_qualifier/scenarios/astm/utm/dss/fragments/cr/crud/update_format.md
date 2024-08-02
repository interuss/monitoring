# Update constraint reference response format test step fragment

This test step fragment validates that updates to constraint references return a body in the correct format.

## 🛑 Mutate constraint reference response format conforms to spec check

The response to a successful constraint reference mutation query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.
