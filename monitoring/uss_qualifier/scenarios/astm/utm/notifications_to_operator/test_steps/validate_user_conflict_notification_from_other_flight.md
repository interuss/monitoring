# Validate conflict notification to user due to other flight test step fragment

This step verifies that the tested USS sent the required notification to the user of an operational intent due to another conflicting new or modified operational intent.

## 🛑 Conflict notifications logs retrievable check
If the query to tested USS fails or uss_qualifier is otherwise unable to retrieve the conflict notifications, this check will fail per
**[interuss.automated_testing.flight_planning.ImplementAPI](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.

## 🛑 Response is valid check
If the conflict notification details are not in the expected format, this check will fail per
**[interuss.automated_testing.flight_planning.ImplementAPI](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.

## 🛑 Presence of notification check
If the required conflict notification to the user is not present, this check will fail per **[astm.f3548.v21.SCD0095](../../../../../requirements/astm/f3548/v21.md)**

## 🛑 Number of notifications check
If exactly one notification to the user per detected conflict is not present, this check will fail per **[astm.f3548.v21.SCD0095](../../../../../requirements/astm/f3548/v21.md)**

## 🛑 Performance evaluation of conflict notification data check
If notification exceeds the 99 percentile wait time of 7 seconds, the tested USS provider does not meet **[astm.f3548.v21.SCD0095](../../../../../requirements/astm/f3548/v21.md)**.

#### Note
As per **[astm.f3548.v21.SCD0095](../../../../../requirements/astm/f3548/v21.md)**, a conflict notification should be
sent by the USS to a user affected by a new or modified operational intent. 
The notification should be sent in no more than
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

ConflictingOIMaxUserNotificationTime is measured from t_time_start - detection of conflict with existing operational intent by USS - till time end - conflict notice sent to affected user.
To make sure the test driver gives enough time for a conflict notification to be sent to the user,
it marks the time to get conflict notifications from tested USS as - the time the expected result of the
injected operational intent from the DSS is verified by the test driver plus 12 seconds.

The sequence of events is - 
1. Test driver initiates plan to tested USS. t0
2. Tested USS shares the plan with DSS and receives DSS response. 
3. USS detects conflict with existing operational intent. 
4. USS notifies managing USS of affected operational intent (if needed) t_time_start
5. Tested USS responds to test driver with expected result. 
6. Test driver checks for shared operational_intent in DSS and verifies that it has the expected result. t1
7. Test driver waits for 12 seconds.
8. Test driver retrieves conflict notifications from tested USS. t1 + 12 seconds
9. Test driver should verify that the conflict notification was sent to the user within 7 seconds of time t1.

We know from above that waiting from t_time_start for 12 seconds would
give us 99% confidence that we receive the notifications. But, the test driver doesn't have access to t_time_start.
So, it starts waiting from a point of time after the t_time_start that is t1.
This ensures that test driver waits for a long enough duration before getting the interactions. Hence, we get
a high confidence that the test driver correctly verifies if a notification was sent by tested_uss.
