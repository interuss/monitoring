# Read subscription test step fragment

This test step fragment validates that subscriptions can be read.

## [Read query succeeds](./read_query.md)

Check query succeeds.

## 🛑 Get subscription response format conforms to spec check

The response to a successful get subscription query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## [Validate subscription fields](../validate/correctness.md)

## [Validate version fields](../validate/non_mutated.md)
