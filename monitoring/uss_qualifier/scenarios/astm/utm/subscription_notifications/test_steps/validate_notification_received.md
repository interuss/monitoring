# Validate notification received test step fragment

This step verifies that a USS under test successfully received a notification about a relevant operational intent from a mock USS instance.
This is done by checking the interactions of that Mock USS instance.

## 🛑 Mock USS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.
Mock USS provides a GET endpoint to retrieve all the interactions between Mock USS and other USSes after a particular time.
If there is any error retrieving these interactions, this check will fail.
These interactions also include the notifications sent and received by Mock USS.

## ⚠️ Expect Notification received with expected subscription_id check
As per **[astm.f3548.v21.SCD0080](../../../../../requirements/astm/f3548/v21.md)**, USSes shall maintain awareness of
operational intents relevant to their own ones when they are in the Activated, NonConforming or Contingent states.
In DSS, there is a subscription associated with an operational intent managed by a USS. A USS under test should successfully
receive a notification of relevant intent from Mock USS based on this subscription.
This check will fail if USS under test does not respond with http status 204 to a valid notification attempt by Mock USS.

## ⚠️ Expect Notification received with expected subscription_id check
The notification received by USS under test should include the expected subscription_id associated with its managed operation.
The check will fail if it does not include the expected subscription_id, as it shows the USS under test did not validate the subscription_id.
