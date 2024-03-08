# Read subscription test step fragment

This test step fragment validates that subscriptions can be read.

## 🛑 Get Subscription by ID check

If a subscription cannot be queried using its ID, the DSS is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Get subscription response format conforms to spec check

The response to a successful get subscription query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Successful subscription search query check

If the DSS fails to let us search in the area for which the subscription was created, it is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Created Subscription is in search results check

If the existing subscription is not returned in a search that covers the area it was created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
