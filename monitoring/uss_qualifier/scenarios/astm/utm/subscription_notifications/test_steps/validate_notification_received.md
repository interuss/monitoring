# Validate notification received test step fragment

This step verifies that a Tested USS successfully received a notification about a relevant operational intent from a Mock USS instance.
This is done by checking the interactions of that Mock USS instance.

## 🛑 Mock USS interactions logs retrievable check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.
Mock USS provides a GET endpoint to retrieve all the interactions that took place between Mock USS
and other USSes after a particular time.
If there is any error retrieving these interactions, this check will fail.
These interactions also include the notifications sent and received by Mock USS.

## ⚠️ Mock USS sends valid notification check
There is an assumption here that DSS shared the correct subscriber information with Mock USS in response to planning or modifying its operational intent.

As per **[astm.f3548.v21.USS0005](../../../../../requirements/astm/f3548/v21.md)**,
Mock USS should send valid notification to USSes subscribed in the area.
The validation of notification involves checking that Mock USS included the correct subscription_id in the notification.
The check will fail if the notification to tested USS does not include the expected subscription_id.

## ⚠️ Tested USS receives valid notification check
As per **[astm.f3548.v21.SCD0080](../../../../../requirements/astm/f3548/v21.md)**, USSes shall maintain awareness of
operational intents relevant to their own ones when they are in the Activated, NonConforming or Contingent states.
In DSS, there is a subscription associated with an operational intent managed by a USS. A tested USS should successfully
receive a notification of relevant intent from Mock USS based on this subscription.
The check will be done if valid notification is sent by Mock USS, which is determined in in
 **[Mock USS sends valid notification check](#⚠️-mock-uss-sends-valid-notification-check)** above.
This check will fail if tested USS does not respond with http status 204 to a valid notification attempt by Mock USS.

## ⚠️ Tested USS rejects invalid notification check

As per **[astm.f3548.v21.USS0105](../../../../../requirements/astm/f3548/v21.md)**, Tested USS should validate that the notification
received includes the subscription_id associated with its managed operation.
The check will be done if invalid notification is sent by Mock USS, which is determined in
 **[Mock USS sends valid notification check](#⚠️-mock-uss-sends-valid-notification-check)** above.
This check will fail if tested USS does not respond with http status 400 for an invalid notification attempt by Mock USS.


