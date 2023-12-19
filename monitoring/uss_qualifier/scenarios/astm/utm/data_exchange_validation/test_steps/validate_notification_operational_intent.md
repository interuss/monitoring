# Validate notification test step fragment

This step verifies that, when creating or modifying an operational intent, a USS sent the required notification for a relevant subscription owned by a mock_uss instance by checking the interactions of that mock_uss instance.

## 🛑 MockUSS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.

## ⚠️ Expect Notification sent check
As per **[astm.f3548.v21.SCD0085](../../../../../requirements/astm/f3548/v21.md)**, the notification should be sent by a
USS about its operational intent to the subscribing USS in no more than MaxRespondToSubscriptionNotification (5) seconds,
95 percent of the time.
To verify that notification was indeed sent for this check, waiting up to MaxRespondToSubscriptionNotificationSeconds gets us
95 percent confidence in declaring the USS non-compliant if notification is not received.
To ensure the notifications sent are not missed for a test case, we can pick a threshold that gives
a very high (e.g., 99 percent per test) confidence of non-compliance. We can make conservative assumptions
about the distribution of the delays. If we assume that the notification delays have a normal distribution
with 95 percentile at 5 seconds, then with the standard deviation of 3.04, we get the 99 percentile at 7.07 seconds.
Hence, for test cases that check notification sent for an operational intent, we will wait for notifications till threshold
[MaxTimeToWaitForSubscriptionNotificationSeconds](./constants.py)  (rounding to 7 seconds).

#### Note
As per **[astm.f3548.v21.SCD0085](../../../../../requirements/astm/f3548/v21.md)**, MaxRespondToSubscriptionNotification
is measured from time_start - Receipt of subscription notification from DSS -
till time_end - Entity details sent to subscribing USS.
To make sure the test driver gives enough time for notifications to be received by mock_uss,
it marks the time to get interactions from mock_uss as - the time test driver initiates the plan.
The sequence of events is -
1. Test driver initiates plan to tested_uss. t0
2. tested_uss shares the plan with DSS and receives DSS response. t_time_start.
3. tested_uss responds to test driver with Completed.
4. Test driver checks for shared operational_intent in DSS and checks its retrievable. t1
5. Test driver waits for MaxTimeToWaitForSubscriptionNotificationSeconds.
6. Test driver retrieves interactions from mock_uss. t1 + MaxTimeToWaitForSubscriptionNotificationSeconds
7. Test driver should find the notification in these interactions to declare that USS sent notifications.

We know from above that waiting from t_time_start for MaxTimeToWaitForSubscriptionNotificationSeconds would
give us 99% confidence that we receive the notifications. But, test_driver doesn't have access to t_time_start.
So, it starts waiting from a point of time after the t_time_start that is t1.
This ensures that test driver waits for a long enough duration before getting the interactions. Hence, we get
a high confidence that the test driver correctly verifies if a notification was sent by tested_uss.

## 🛑 Notification data is valid check
**[astm.f3548.v21.SCD0085](../../../../../requirements/astm/f3548/v21.md)**
