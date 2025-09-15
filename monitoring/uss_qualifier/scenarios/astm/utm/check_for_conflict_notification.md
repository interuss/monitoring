# Check for conflict notification test step fragment

This test step fragment verifies that a notification reporting the conflict was sent to the UAS personnel.

## 🛑 New notification about conflict check

If the USS doesn't send a notification within ConflictingOIMaxUserNotificationTime + 2 seconds,
then we conclude it is very likely to be in violation of **[astm.f3548.v21.SCD0090](../../../requirements/astm/f3548/v21.md)**, and therefore this check will fail.

Dues to test design, the testing suite cannot verify that notification are occuring at least 95% of the time as stated in the standard and always execpt a notification.
