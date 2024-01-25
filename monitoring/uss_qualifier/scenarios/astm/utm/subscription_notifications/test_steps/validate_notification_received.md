# Validate notification received test step fragment

This step verifies that a USS successfully received a notification about a relevant operational intent from a mock USS instance.
This is done by checking the interactions of that mock_uss instance.

## 🛑 MockUSS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.

## ⚠️ Expect Notification received with expected subscription_id check
As per **[astm.f3548.v21.SCD0080](../../../../../requirements/astm/f3548/v21.md)**, USSes shall maintain awareness of operational intents
relevant to their own ones when they are in the Activated, NonConforming or Contingent states.
The tested_uss would have a subscription id for its operational intent. The tested_uss should successfully
receive a notification of relevant intent sent by mock_uss based on the subscription id.

This check will fail if tested_uss does not respond with http status 204 to mock_uss's notification attempt,
and if the notification does not include the expected subscription_id.
