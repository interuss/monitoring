# USS Availability Sync test step fragment

## 🛑USS Availability is consistent across every DSS instance check

If the reported availability for a USS is not consistent, across a set of DSS instances, with the value that was previously read or set on an arbitrary DSS instance,
either the DSS through which the value was set or the one through which the values was retrieved is failing to meet at least one of these requirements:

**[astm.f3548.v21.DSS0210,3a](../../../../../../requirements/astm/f3548/v21.md)**, if the USS identifier is not properly synced;
**[astm.f3548.v21.DSS0210,3b](../../../../../../requirements/astm/f3548/v21.md)**, if the USS availability is not properly synced;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS returns API calls before having committed the changes to the underlying distributed store.

As a consequence, the DSS also fails to meet **[astm.f3548.v21.DSS0210,A2-7-2,6](../../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑USS Availability version is consistent across every DSS instance check

If the reported availability version for a USS is not consistent, across a set of DSS instances, with the value that was previously read or set on an arbitrary DSS instance,
either the DSS through which the value was set or the one through which the values was retrieved is failing to meet at least one of these requirements:

**[astm.f3548.v21.DSS0210,3c](../../../../../../requirements/astm/f3548/v21.md)**, if the USS availability version is not properly synced;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS returns API calls before having committed the changes to the underlying distributed store.

As a consequence, the DSS also fails to meet **[astm.f3548.v21.DSS0210,A2-7-2,6](../../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.
