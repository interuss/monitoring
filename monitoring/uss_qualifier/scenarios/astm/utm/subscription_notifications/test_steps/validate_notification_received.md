# Validate notification received test step fragment

This step verifies that a Tested USS successfully received a notification about a relevant operational intent from a Mock USS instance.
This is done by checking the interactions of that Mock USS instance.

## [Get Mock USS interactions logs](../../../../interuss/mock_uss/get_mock_uss_interactions.md)
Mock USS provides a GET endpoint to retrieve all the interactions that took place between Mock USS
and other USSes after a particular time.
These interactions also include the notifications sent and received by Mock USS.

## 🛑 Mock USS sends valid notification check
There is an assumption here that DSS shared the correct subscriber information with Mock USS in response to planning or modifying its operational intent.

As per **[astm.f3548.v21.USS0005](../../../../../requirements/astm/f3548/v21.md)**,
Mock USS should send valid notification to USSes subscribed in the area.
The validation of notification involves checking that Mock USS included the correct subscription_id in the notification.
The check will fail if no or more than one notification is sent to the tested USS, or if the notification does not include the expected subscription_id.

## ⚠️ Tested USS receives valid notification check
USSes shall maintain awareness of operational intents relevant to their own ones when they are in the Activated, NonConforming or Contingent states.
In DSS, there is a subscription associated with an operational intent managed by a USS. A tested USS should successfully
receive a notification of relevant intent from Mock USS based on this subscription.

If the tested USS does not respond with an HTTP status 204 to a valid notification sent by the mock USS, then the tested USS
does not maintain awareness of operational intents relevant to their own ones (**[astm.f3548.v21.SCD0080](../../../../../requirements/astm/f3548/v21.md)**), and
does not implement correctly the `notifyOperationalIntentDetailsChanged` operation (**[astm.f3548.v21.USS0105,3](../../../../../requirements/astm/f3548/v21.md)**).
