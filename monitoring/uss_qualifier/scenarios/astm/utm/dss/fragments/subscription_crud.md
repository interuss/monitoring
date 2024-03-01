# CRUD subscription test step fragment

This test step fragment validates that subscriptions can be created, updated, read and modified.

## 🛑 Create subscription query succeeds check

As per **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**, the DSS API must allow callers to create a subscription with either one or both of the
start and end time missing, provided all the required parameters are valid.

## 🛑 Create subscription response is correct check

A successful subscription creation query is expected to return a well-defined body, the content of which reflects the created subscription.
If the format and content of the response are not conforming, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Create subscription response format conforms to spec check

The response to a successful subscription creation query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Response to subscription creation contains a subscription check

As per **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**, upon creation of a subscription,
the newly created subscription must be part of its response.

## 🛑 Get Subscription by ID check

If a subscription cannot be queried using its ID, the DSS is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Get subscription response format conforms to spec check

The response to a successful get subscription query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Successful subscription search query check

If the DSS fails to let us search in the area for which the subscription was created, it is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Created Subscription is in search results check

If the existing subscription is not returned in a search that covers the area it was created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Subscription can be mutated check

If a subscription cannot be modified with a valid set of parameters, the DSS is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Response to subscription mutation contains a subscription check

As per **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**, upon mutation of a subscription,
the newly created subscription must be part of its response.

## ⚠️ Mutate subscription response format conforms to spec check

The response to a successful subscription mutation query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Subscription can be deleted check

An attempt to delete a subscription when the correct version is provided should succeed, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Delete subscription response format conforms to spec check

The response to a successful subscription deletion query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.
