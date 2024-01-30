# Validate subscription test step fragment

This test step fragment attempts to validate a subscription returned by the DSS after its creation or mutation.

## 🛑 Returned subscription has an ID check

If the returned subscription has no ID, **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** is not respected.

## 🛑 Returned subscription ID is correct check

If the returned subscription ID does not correspond to the one specified in the creation parameters,
**[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** is not respected.

## 🛑 Returned notification index is 0 if present check

The notification index of a newly created subscription must be 0, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Returned notification index is equal to or greater than 0 check

If the notification index of the subscription is less than 0, the DSS fails to properly implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Returned subscription has an ISA URL check

If the returned subscription has no ISA URL defined, **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** is not respected.

## 🛑 Returned ISA URL has correct base URL check

The returned ISA URL must be prefixed with the USS base URL that was provided at subscription creation, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Returned subscription has a start time check

If the returned subscription has no start time defined, **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** is not respected.

## 🛑 Returned start time is correct check

The returned start time must be the same as the provided one, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Returned subscription has an end time check

Subscriptions need a defined end time in order to limit their duration: if the DSS omits to set the end time, it will be in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Returned end time is correct check

The returned end time must be the same as the provided one, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Returned subscription has a version check

If the returned subscription has no version defined, **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** is not respected.

## 🛑 Non-mutated subscription keeps the same version check

If the version of the subscription is updated without there having been any mutation of the subscription, the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Mutated subscription version is updated check

Following a mutation, the DSS needs to update the subscription version, otherwise it is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Non-implicit subscription has implicit flag set to false check

A subscription that was explicitly created by a client should always have its `implicit_subscription` flag set to false,
otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Operational intents notification flag is as requested check

If the subscription was created with the `include_operational_intents` flag set to true, the returned subscription must have the same flag set to true, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Constraints notification flag is as requested check

If the subscription was created with the `include_constraints` flag set to true, the returned subscription must have the same flag set to true, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.
