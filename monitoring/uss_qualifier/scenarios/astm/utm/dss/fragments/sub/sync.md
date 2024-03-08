# Synchronize subscription test step fragment

This test step fragment validates that subscriptions are properly synchronized across a set of DSS instances.

## 🛑 Subscription can be found at every DSS check

If the previously created or mutated subscription cannot be found at a DSS, either one of the instances at which the subscription was created or the one that was queried,
may be failing to implement **[astm.f3548.v21.DSS0210,1a](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct USS base URL check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct USS base URL,
either one of the instances at which the subscription was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,1c](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct start time check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct start time,
either one of the instances at which the subscription was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,1e](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct end time check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct end time,
either one of the instances at which the subscription was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,1e](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct version check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct version,
either one of the instances at which the subscription was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,1f](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct notification flags check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct notification flags,
either one of the instances at which the subscription was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,1g](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct implicit flag check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct implicit flag,
either one of the instances at which the subscription was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,1h](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains expected notification count check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the expected notification count,
either one of the instances at which the subscription was created or the one that was queried, may be failing to implement **[astm.f3548.v21.DSS0210,1i](../../../../../../requirements/astm/f3548/v21.md)**.
