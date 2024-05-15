# Validate conflict notification to user of new or modified flight test step fragment

This step verifies that when creating or modifying an operational intent, the tested USS sent the required notification to the user of the new or modified conflicting operational intent.

## 🛑 Conflict notifications logs retrievable check
If the query to tested USS fails or the test driver is otherwise unable to retrieve the conflict notifications, this check will fail per
**[interuss.automated_testing.flight_planning.ImplementAPI](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.

## 🛑 Response is valid check
If the conflict notification details are not in the expected format, this check will fail per
**[interuss.automated_testing.flight_planning.ImplementAPI](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.

## 🛑 Presence of notification check
If the required conflict notification to the user is not present, this check will fail per **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**

## ⚠️ Number of notifications check
If exactly one notification to the user per detected conflict is not present, this check will fail per **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**

## ⚠️ Performance evaluation of conflict notification data check
As per **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**, a conflict notification should be
sent by the USS to the user of a new or modified operational intent. 
The notification should be sent in no more than
ConflictingOIMaxUserNotificationTime (5) seconds, 95 percent of the time.
To verify that the notification was indeed sent for this check, waiting up to
ConflictingOIMaxUserNotificationTime gets us 95 percent confidence in declaring the USS non-compliant if
the notification is not received.
To ensure the notifications sent are not missed for a test case, we can pick a threshold that gives
a very high (e.g., 99 percent per test) confidence of non-compliance. We can make conservative assumptions
about the distribution of the delays. If we assume that the notification delays have a normal distribution
with 95 percentile at 5 seconds, then with the standard deviation of 3.04, we get the 99 percentile at 7.07 seconds.
If notification exceeds the 99 percentile wait time of 7 seconds, the tested USS provider does not meet **[astm.f3548.v21.SCD0090](../../../../../requirements/astm/f3548/v21.md)**.
