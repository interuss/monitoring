# Ensure clean workspace test step fragment

Ensure a clean workspace for testing interactions with a DSS by removing any operational intent references from the DSS that may have been left behind from testing efforts.

## 🛑 Operational intent references can be queried by ID check

If an existing operational intent reference cannot directly be queried by its ID, or if for a non-existing one the DSS replies with a status code different than 404,
the DSS implementation is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Operational intent references can be searched for check

A client with valid credentials should be allowed to search for operational intents in a given area.
Otherwise, the DSS is not in compliance with **[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Operational intent reference removed check

If an existing operational intent cannot be deleted when providing the proper ID and OVN, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.
