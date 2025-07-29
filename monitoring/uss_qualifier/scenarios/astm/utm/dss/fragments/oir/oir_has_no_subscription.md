# OIR is attached to no subscription test step fragment

## [Verify query succeeds](./crud/read_query.md)

## 🛑 OIR is not attached to a subscription check

If the OIR returned by the DSS under test is not attached to a subscription,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../requirements/astm/f3548/v21.md)**

## 🛑 Subscription referenced by the OIR does not exist check

Attempt to fetch the subscription referenced by the OIR in order to confirm that it does not exist.

This check will fail if the DSS under test does not return a 400 or 404 error when the subscription
that it reported in the OIR is queried, as the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../requirements/astm/f3548/v21.md)**.

This check is run in circumstances where the subscription is expected to not exist, and will result in attempts
to obtain the _null_ subscription ID with value `00000000-0000-4000-8000-000000000000`, unless the DSS instances
under test chose to use another placeholder for non-existent subscriptions.

