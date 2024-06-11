# Implicit subscription validity test step fragment

This test step fragment validates the time-bounds of an implicit subscription

## 🛑 Implicit subscription has correct temporal parameters check

If the implicit subscription time boundaries do not match the OIR's, either one, or both, of the following are possible:

The DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../requirements/astm/f3548/v21.md)**, as the implicit subscription does not cover the OIR's time boundaries;
Entities that should have been cleaned up earlier are still present in the DSS, and this scenario cannot proceed.
