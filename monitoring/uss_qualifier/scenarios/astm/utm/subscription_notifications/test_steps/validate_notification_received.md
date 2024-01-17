# Validate notification received test step fragment

This step verifies that, a USS successfully received notification due to subscription, for a relevant intent from mock_uss instance by checking the interactions of that mock_uss instance.

## 🛑 MockUSS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.

## ⚠️ Expect Notification received check
As per **[astm.f3548.v21.SCD0080](../../../../../requirements/astm/f3548/v21.md)**, shall maintain awareness of relevant
operational intents when its managed operation is in Activated, NonConforming or Contingent state.
The tested_uss would have a subscription id for its operational intent. The tested_uss should successfully
receive a notification of relevant intent sent by mock_uss based on the subscription id.
