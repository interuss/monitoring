# Validate no notification test step fragment

This step verifies when a flight is not created, it is also not notified by checking the interuss interactions of mock_uss instance.

## 🛑 MockUSS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.

## 🛑 Expect Notification not sent check

**[interuss.f3548.notification_requirements.NoDssEntityNoNotification](../../../../../requirements/interuss/f3548/notification_requirements.md)**

As per the above requirement, the notification should not be sent by a USS about an entity that could not be created in DSS
to any USS. To verify that notification was indeed not sent, we need to wait and check up to a threshold to get confidence
that USS did not send notification.
The max duration for sending a notification in [SCD0085](../../../../../requirements/astm/f3548/v21.md) is MaxRespondToSubscriptionNotification(5) seconds.
However, this duration is from time start - Receipt of subscription notification from DSS, which does not exist for this check.
In this check we use time start when the test driver asked the USS to plan the failed flight.
When checking notification not sent, we should wait for the same duration that is used for when checking notification sent.
[Expect Notification sent](./validate_notification_operational_intent.md).
So, we plan to use [MaxTimeToWaitForSubscriptionNotificationSeconds](./constants.py) (7 seconds).
