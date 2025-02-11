# User notification retrieval test step fragment

This test step fragment documents the retrieval of user notifications.

In this step, uss_qualifier retrieve notifications for each SP under test.

## 🛑 Successful user notifications retrieval check

Per **[interuss.automated_testing.rid.injection.UserNotificationsSuccess](../../../../../requirements/interuss/automated_testing/rid/injection.md)**, the retrieval of users notifications should succeed for every NetRID Service Provider under test.

**[astm.f3411.v19.NET0500](../../../../../requirements/astm/f3411/v19.md)** requires a Service Provider to provide a persistently supported test instance of their implementation.
This check will fail if notifications cannot be successfully retrieved
