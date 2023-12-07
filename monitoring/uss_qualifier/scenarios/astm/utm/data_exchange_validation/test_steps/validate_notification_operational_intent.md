# Validate notification test step fragment

This step verifies that, when creating or modifying an operational intent, a USS sent the required notification for a relevant subscription owned by a mock_uss instance by checking the interactions of that mock_uss instance.

## MockUSS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.

## `Expect Notification sent check`
**[astm.f3548.v21.SCD0085](../../../../../requirements/astm/f3548/v21.md)**
As per the requirement, the notification should be sent by a USS about its operational intent
to the subscribing USS in no more than MaxRespondToSubscriptionNotification (5) seconds, 95 percent of the time.
To verify that notification was indeed sent for this check, waiting up to MaxRespondToSubscriptionNotificationSeconds gets us
95 percent confidence in declaring the USS non-compliant if notification is not received.
To ensure the notifications sent are not missed for a test case, we can pick a threshold that gives
a very high (e.g., 99 percent per test) confidence of non-compliance. We can make conservative assumptions
about the distribution of the delays. If we assume that the notification delays have a normal distribution
with 95 percentile at 5 seconds, then with the standard deviation of 3.04, we get the 99 percentile at 7.07 seconds.
Hence, for test cases that check notification sent for an opertional intent, we will wait for notifications till threshold
[MaxTimeToWaitForSubscriptionNotificationSeconds](./constants.py)  (rounding to 7 seconds).
####Note -
MaxRespondToSubscriptionNotification is measured from time start - Receipt of subscription notification
from DSS - till time end - Entity details sent to subscribing USS.
However, this check start time is w.r.t the time test driver initiated a plan, we would need to add some additional time to
MaxTimeToWaitForSubscriptionNotificationSeconds to account for processing time taken by a USS on receipt of the plan. And the time end for this check is when mock_uss received the notification,
so the network delay in time taken for notification to reach mock_uss, should also be included. How much more time should be added to the wait time?


## Notification data is valid check
**[astm.f3548.v21.SCD0085](../../../../../requirements/astm/f3548/v21.md)**
