# Update subscription without query-related check test step fragment

This test step fragment validates that subscriptions can be updated but does not contain a check related to the query itself.

This fragment is intended to be used in scenarios that define their own query verification check, usually when more specific requirements are being tested.

## 🛑 Mutate subscription response format conforms to spec check

The response to a successful subscription mutation query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Mutate subscription response content is correct check

A successful subscription mutation query is expected to return a well-defined body, the content of which reflects the mutated subscription.

If the content of the response does correspond to the requested mutation, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## [Validate subscription fields](../validate/correctness.md)

## [Validate version fields](../validate/mutated.md)
