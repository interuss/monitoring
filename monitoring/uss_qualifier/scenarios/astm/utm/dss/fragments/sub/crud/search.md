# Search subscription test step fragment

This test step fragment validates that subscriptions can be searched for.

## 🛑 Successful subscription search query check

If the DSS fails to let us search in the area for which the subscription was created, it is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Created Subscription is in search results check

If the existing subscription is not returned in a search that covers the area it was created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
