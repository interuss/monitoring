# Synchronize operational intent reference test step fragment

This test step fragment validates that operational intent references are properly synchronized across a set of DSS instances.

## 🛑 Operational intent reference can be found at every DSS check

If the previously created or mutated operational intent reference cannot be found at a DSS, either one of the instances at which the operational intent reference was created or the one that was queried,
may be failing to implement **[astm.f3548.v21.DSS0210,2a](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated operational intent reference general area is synchronized check

When querying a secondary DSS for operational intents in the planning area that contains the propagated operational
intent, if the propagated operational intent is not contained in the response, then the general area in which the
propagated operational intent is located is not synchronized across DSS instances.
As such, either the primary or the secondary DSS fails to properly implements **[astm.f3548.v21.DSS0210,2e](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Propagated operational intent reference contains the correct manager check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct manager,
either one of the instances at which the operational intent reference was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,2b](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Propagated operational intent reference contains the correct USS base URL check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct USS base URL,
either one of the instances at which the operational intent reference was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,2c](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Propagated operational intent reference contains the correct state check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct state,
either one of the instances at which the operational intent reference was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,2d](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Propagated operational intent reference contains the correct start time check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct start time,
either one of the instances at which the operational intent reference was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,2f](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Propagated operational intent reference contains the correct end time check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct end time,
either one of the instances at which the operational intent reference was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,2f](../../../../../../requirements/astm/f3548/v21.md)**.
