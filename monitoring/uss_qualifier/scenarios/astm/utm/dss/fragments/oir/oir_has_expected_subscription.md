# OIR is attached to expected subscription test step fragment

## [Query Success](./crud/read_query.md)

Check query succeeds

## 🛑 OIR is attached to expected subscription check

If the OIR returned by the DSS under test is not attached to the expected subscription,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../requirements/astm/f3548/v21.md)**

## [Get referenced Subscription](../sub/crud/read_query.md)

Attempt to fetch the subscription referenced by the OIR in order to confirm that it does not exist.

This is only used in circumstances where the subscription is expected to not exist and the DSS implementation
is not using the _null_ subscription ID with value `00000000-0000-4000-8000-000000000000`.
