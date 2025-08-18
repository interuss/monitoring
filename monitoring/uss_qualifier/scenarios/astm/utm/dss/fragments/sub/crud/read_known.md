# Read subscription test step fragment

This test step fragment validates that a known subscriptions can be read, and that its content is correct.

## [Verify read query succeeds](./read_query.md)

## 🛑 Get subscription response format conforms to spec check

The response to a successful get subscription query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Get subscription response content is correct check

A successful query for a subscription is expected to return a body, the content of which reflects the created subscription.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.

## [Validate subscription fields](../validate/correctness.md)

## [Validate version fields](../validate/non_mutated.md)
