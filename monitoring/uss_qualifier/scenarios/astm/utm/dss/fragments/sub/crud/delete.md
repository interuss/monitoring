# Delete subscription test step fragment

This test step fragment validates that subscriptions can be deleted.

## 🛑 Subscription can be deleted check

An attempt to delete a subscription when the correct version is provided should succeed, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Delete subscription response format conforms to spec check

The response to a successful subscription deletion query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
