# Update subscription test step fragment

This test step fragment validates that subscriptions can be updated.

## 🛑 Subscription can be mutated check

If a subscription cannot be modified with a valid set of parameters, the DSS is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Response to subscription mutation contains a subscription check

As per **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**, upon mutation of a subscription,
the newly created subscription must be part of its response.

## ⚠️ Mutate subscription response format conforms to spec check

The response to a successful subscription mutation query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
