# Clear area validation test step fragment

uss_qualifier verifies with the DSS that there are no operational intents remaining in the area.

## 🛑 DSS responses check

If the DSS fails to reply to a query concerning operational intent references in a given area, or fails to allow the deletion of
an operational intent from its own creator, it is in violation of **[astm.f3548.v21.DSS0005,1](../../../requirements/astm/f3548/v21.md)**
or **[astm.f3548.v21.DSS0005,2](../../../requirements/astm/f3548/v21.md)**, and this check will fail.

## 🛑 Area is clear of op intents check

If operational intents exist in the 4D area(s) that should be clear, then the current state of the test environment is not suitable to conduct tests so this check will fail.
