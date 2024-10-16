# OIR's subscription can be updated test step fragment

## [Update the OIR's subscription](./crud/update_query.md)

This step verifies that an OIR attached to an explicit subscription can be mutated in order to be attached
to another explicit subscription that properly covers the extent of the OIR.

## [Fetch the OIR](./crud/read_query.md)

To determine if the OIR is attached to the correct subscription, the OIR is directly fetched from the DSS.

## 🛑 OIR is attached to expected subscription check

If the OIR returned by the DSS under test is not attached to the expected subscription,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../requirements/astm/f3548/v21.md)**
