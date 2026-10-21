# Subscriptions unchanged after rejected request test step fragment

This test step fragment validates that a request to create or mutate an operational intent reference that was rejected
because of a conflict did not create, modify or delete any subscription, including implicit subscriptions.

The subscriptions owned by the client within the planning area are queried before and after the rejected request, and compared.

## 🛑 Successful subscription search query check

**[astm.f3548.v21.DSS0005,5](../../../../../../requirements/astm/f3548/v21.md)** requires the implementation of the DSS endpoint to allow callers to retrieve the subscriptions they created.

## ⚠️ Rejected request did not create or modify subscriptions check

A request to create or mutate an operational intent reference that is rejected because of missing OVNs is not expected to have any effect.
In particular, the DSS is not expected to create an implicit subscription requested by such a request, nor to expand
an existing implicit subscription to cover the rejected operational intent reference.

If the subscriptions owned by the client differ before and after the rejected request, the DSS fails to properly manage
implicit subscriptions and is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../requirements/astm/f3548/v21.md)**.
