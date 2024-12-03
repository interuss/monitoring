# Ensure clean workspace test step fragment

Ensure a clean workspace for testing interactions with a DSS by removing any subscriptions from the DSS that may have been left behind from testing efforts.

## 🛑 Successful subscription search query check

**[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** requires the implementation of the DSS endpoint to allow callers to retrieve the subscriptions they created.

## 🛑 Subscription can be queried by ID check

If the DSS cannot be queried for the existing test ID, the DSS is likely not implementing **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** correctly.

## 🛑 Subscription can be deleted check

**[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** requires the implementation of the DSS endpoint to allow callers to delete subscriptions they created.
