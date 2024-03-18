# Synchronize subscription test step fragment

This test step fragment validates that subscriptions are properly synchronized across a set of DSS instances.

## 🛑 Subscription can be found at every DSS check

If the previously created or mutated subscription cannot be found at a DSS, either one of the instances at which the subscription was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,1a](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct USS base URL check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct USS base URL,
either one of the instances at which the subscription was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,1c](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct start time check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct start time,
either one of the instances at which the subscription was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,1e](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct end time check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct end time,
either one of the instances at which the subscription was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,1e](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct version check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct version,
either one of the instances at which the subscription was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,1f](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct notification flags check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct notification flags,
either one of the instances at which the subscription was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,1g](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains the correct implicit flag check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the correct implicit flag,
either one of the instances at which the subscription was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,1h](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Propagated subscription contains expected notification count check

If the subscription returned by a DSS to which the subscription was synchronized to does not contain the expected notification count,
either one of the instances at which the subscription was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,1i](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Secondary DSS returns the subscription in searches for area that contains it check

The secondary DSS should be aware of the subscription's area: when a search query is issued for an area that encompasses the created subscription,
the secondary DSS should return the subscription in its search results.

Otherwise, it is in violation of one of the following requirements:

**[astm.f3548.v21.DSS0210,1d](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Secondary DSS does not return the subscription in searches not encompassing the general area of the subscription check

The secondary DSS should be aware of the subscription's area: when a search query is issued for an area not in the vicinity of the created subscription,
the secondary DSS should not return it in its search results.

Otherwise, it is in violation of one of the following requirements:

**[astm.f3548.v21.DSS0210,1d](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.
