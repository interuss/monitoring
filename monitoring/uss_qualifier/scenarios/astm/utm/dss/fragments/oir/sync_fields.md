# Synchronize operational intent reference fields test step fragment

This test step fragment validates that operational intent reference attributes are properly synchronized across a set of DSS instances.

## ⚠️ Propagated operational intent reference contains the correct manager check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct manager,
either one of the instances at which the operational intent reference was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,2b](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Propagated operational intent reference contains the correct USS base URL check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct USS base URL,
either one of the instances at which the operational intent reference was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,2c](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Propagated operational intent reference contains the correct state check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct state,
either one of the instances at which the operational intent reference was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,2d](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Propagated operational intent reference contains the correct start time check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct start time,
either one of the instances at which the operational intent reference was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,2f](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Propagated operational intent reference contains the correct end time check

If the operational intent reference returned by a DSS to which the operational intent reference was synchronized to does not contain the correct end time,
either one of the instances at which the operational intent reference was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,2f](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.
