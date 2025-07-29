# Validate subscription test step fragment

This test step fragment attempts to validate the content of a single subscription returned by the DSS.

The code for these checks lives in the [subscription_validator.py](../../../validators/subscription_validator.py) class.

## ⚠️ Returned subscription ID is correct check

If the returned subscription ID does not correspond to the one specified in the creation parameters,
**[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned subscription has an USS base URL check

If the returned subscription has no USS base URL defined, **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned USS base URL has correct base URL check

The returned USS base URL must be prefixed with the USS base URL that was provided at subscription creation, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned subscription has a start time check

If the returned subscription has no start time defined, **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned start time is correct check

The returned start time must be the same as the provided one, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned subscription has an end time check

Subscriptions need a defined end time in order to limit their duration: if the DSS omits to set the end time, it will be in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned end time is correct check

The returned end time must be the same as the provided one, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned subscription has a version check

If the returned subscription has no version defined, **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Non-implicit subscription has implicit flag set to false check

A subscription that was explicitly created by a client should always have its `implicit_subscription` flag set to false,
otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Operational intents notification flag is as requested check

If the subscription was created with the `include_operational_intents` flag set to true, the returned subscription must have the same flag set to true, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Constraints notification flag is as requested check

If the subscription was created with the `include_constraints` flag set to true, the returned subscription must have the same flag set to true, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
