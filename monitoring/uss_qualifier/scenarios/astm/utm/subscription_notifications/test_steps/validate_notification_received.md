# Validate notification received test step fragment

This step verifies that a USS successfully received a notification about a relevant operational intent from a mock USS instance.
This is done by checking the interactions of that mock_uss instance.

## 🛑 MockUSS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.
Mock_uss provides a GET endpoint to retrieve all the interactions between mock_uss and other USSes after a particular time.
If there is any error retrieving these interactions, this check will fail.
These interactions also include the notifications sent and received by mock_uss.

## ⚠️ Expect Notification received with expected subscription_id check
As per **[astm.f3548.v21.SCD0080](../../../../../requirements/astm/f3548/v21.md)**, USSes shall maintain awareness of operational intents
relevant to their own ones when they are in the Activated, NonConforming or Contingent states.
There is a subscription associated with the managed operation of tested_uss, in DSS. The tested_uss should successfully
receive a notification of relevant intent from mock_uss based on this subscription.
This check will fail if tested_uss does not respond with http status 204 to mock_uss's notification attempt.

## ⚠️ Expect Notification received with expected subscription_id check
The notification received by tested_uss should include the expected subscription_id associated with its managed operation.
The check will fail if it does not include the expected subscription_id, as it shows the tested_uss did not validate the subscription_id.
