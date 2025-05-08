# OIR is attached to expected subscription test step fragment

## [Verify query succeeds](./crud/read_query.md)

## 🛑 OIR is attached to the NULL subscription check

If the OIR returned by the DSS under test is not attached to the expected subscription,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../requirements/astm/f3548/v21.md)**

## 🛑 Subscription referenced by the OIR does not exist check

Attempt to fetch the subscription referenced by the OIR in order to confirm that it does not exist.

This check will fail if the DSS under test does not return a 400 or 404 error when the subscription
that it reported in the OIR is queried.

This is only used in circumstances where the subscription is expected to not exist and the DSS implementation
is not using the _null_ subscription ID with value `00000000-0000-4000-8000-000000000000`.
