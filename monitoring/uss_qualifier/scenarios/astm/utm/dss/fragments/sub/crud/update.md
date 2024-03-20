# Update subscription test step fragment

This test step fragment validates that subscriptions can be updated.

## 🛑 Subscription can be mutated check

If a subscription cannot be modified with a valid set of parameters, the DSS is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Mutate subscription response format conforms to spec check

The response to a successful subscription mutation query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Mutate subscription response content is correct check

A successful subscription mutation query is expected to return a well-defined body, the content of which reflects the mutated subscription.

If the content of the response does correspond to the requested mutation, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
