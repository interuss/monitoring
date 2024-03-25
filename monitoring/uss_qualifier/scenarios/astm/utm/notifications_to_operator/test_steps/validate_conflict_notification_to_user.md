# Validate conflict notification to user test step fragment

This step verifies that when creating or modifying an operational intent, the tested USS sent the required notification to the user of a conflicting operational intent.

## 🛑 Tested USS conflict notifications logs retrievable check

If the query to tested USS fails or uss_qualifier is otherwise unable to retrieve the conflict notifications, the tested USS provider does not meet
**[interuss.tested_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/tested_uss/hosted_instance.md)**.

## ⚠️ Expect conflict notification sent check
As per **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**, a conflict notification should be
sent by the USS to the affected user of a new or modified operational intent in no more than
ConflictingOIMaxUserNotificationTime (5) seconds, 95 percent of the time.
To verify that the notification was indeed sent for this check, waiting up to
ConflictingOIMaxUserNotificationTime gets us 95 percent confidence in declaring the USS non-compliant if
the notification is not received.
To ensure the notifications sent are not missed for a test case, we can pick a threshold that gives
a very high (e.g., 99 percent per test) confidence of non-compliance. We can make conservative assumptions
about the distribution of the delays. If we assume that the notification delays have a normal distribution
with 95 percentile at 5 seconds, then with the standard deviation of 3.04, we get the 99 percentile at 7.07 seconds.
In addition, due to potential delays in the test harness setup, an additional 5 seconds is allowed. Hence,
for test cases that check notification sent for an operational intent, we will wait for notifications until a threshold of 12 seconds (rounded).

#### Note
As per **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**, ConflictingOIMaxUserNotificationTime
is measured from time_start - detection of conflict with existing operational intent by USS - till time end - conflict notice sent to affected user.
To make sure the test driver gives enough time for a conflict notification to be sent to the user,
it marks the time to get conflict notifications from tested USS as - the time the expected result of the
injected operational intent from the DSS is verified by the test driver plus 12 seconds.
The sequence of events is -
1. Test driver initiates plan to tested USS. t0
2. Tested USS shares the plan with DSS and receives DSS response. 
3. USS detects conflict with existing operational intent. t_time_start
4. Tested USS responds to test driver with expected response. 
5. Test driver checks for shared operational_intent in DSS and checks its retrievable. t1
6. Test driver waits for 12 seconds.
7. Test driver retrieves conflict notifications from tested USS. t1 + 12 seconds
8. Test driver should verify that the conflict notification was sent to the user within 7 seconds of time t1.

We know from above that waiting from t_time_start for 12 seconds would
give us 99% confidence that we receive the notifications. But, the test driver doesn't have access to t_time_start.
So, it starts waiting from a point of time after the t_time_start that is t1.
This ensures that test driver waits for a long enough duration before getting the interactions. Hence, we get
a high confidence that the test driver correctly verifies if a notification was sent by tested_uss.

## 🛑 Conflict notification data is valid check
If data is not correct or exceeds the 99 percentile wait time of 7 seconds, the tested USS provider does not meet **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**.
