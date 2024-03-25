# Validate conflict notification to user test step fragment

This step verifies that when creating or modifying an operational intent, the tested USS sent the required notification to the user of a conflicting operational intent.

## 🛑 Tested USS conflict notifications logs retrievable check

If the query to tested USS fails or uss_qualifier is otherwise unable to retrieve the conflict notifications, the tested USS provider does not meet
**[User notification test design document](https://docs.google.com/document/d/1yCBxm-vzDVo37D9JEy4ROWvepO0w9FW4LQ5kVqgoiQg/edit)**.

## ⚠️ Expect conflict notification sent check
As per **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**, the notification should be sent by a USS about its operational intent to the affected user is no more than ConflictingOIMaxUserNotificationTime (5) seconds, 95 percent of the time.
To verify that notification was indeed sent for this check, waiting up to ConflictingOIMaxUserNotificationTime gets us
95 percent confidence in declaring the USS non-compliant if notification is not received.
To ensure the notifications sent are not missed for a test case, we can pick a threshold that gives
a very high (e.g., 99 percent per test) confidence of compliance. We can make conservative assumptions
about the distribution of the delays. If we assume that the notification delays have a normal distribution
with 95 percentile at 5 seconds, then with the standard deviation of 3.04, we get the 99 percentile at 7.07 seconds.
In addition, due to potential delays in the test harness setup, an additional 5 seconds is allowed. Hence, for test cases that check whether a notification is sent to the user associated with an operational intent, wait for notifications until a total threshold of 12 seconds (rounding down).

#### Note
As per **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**, ConflictingOIMaxUserNotificationTime
is measured from time_start - operational intent conflict identified by USS -
till time_end - Conflict notification sent to affected user.
To make sure the test driver gives enough time for conflict notifications to be sent by the tested USS,
it marks the time to get conflict notifications from tested USS as the time the test driver verifies the correct result of the planned conflicting operational intent in the DSS to a time of 12 seconds later.
The sequence of events is -
1. Test driver initiates plan to tested USS. t0
2. Tested USS shares the plan with DSS and receives DSS response. 
3. Tested USS detects conflict. t_time_start.
3. Tested USS responds to test driver with Completed or Rejected (as appropriate).
4. Test driver checks for shared operational intents in DSS and checks that expected operational intents are retrievable and in expected states. t1
5. Test driver waits for 12 seconds.
6. Test driver retrieves conflict notifications from tested USS. t1 + 12 seconds
7. Test driver should find the conflict notification to the user to declare that USS sent required notification.

We know from above that waiting from t_time_start for 7 seconds would give us 99% confidence that we receive the notifications, but the test driver doesn't have access to t_time_start.
So instead, the wait time starts point t1 just after t_time_start.
This ensures that test driver waits for a long enough duration before getting the conflict notifications.
Hence, we get a high confidence that the test driver correctly verifies that a conflict notification was sent by tested USS.

## 🛑 Conflict notification data is valid check
If data is not correct or exceeds the 99 percentile wait time of 7 seconds, the tested USS provider does not meet **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**.
