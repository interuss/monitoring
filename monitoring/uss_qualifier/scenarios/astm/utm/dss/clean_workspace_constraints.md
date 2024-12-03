# Ensure clean workspace test step fragment

Ensure a clean workspace for testing interactions with a DSS by removing any constraint references from the DSS that may have been left behind from testing efforts.

## 🛑 Constraint references can be queried by ID check

If an existing constraint reference cannot directly be queried by its ID, or if for a non-existing one the DSS replies with a status code different than 404,
the DSS implementation is in violation of **[astm.f3548.v21.DSS0005,3](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Constraint references can be searched for check

A client with valid credentials should be allowed to search for constraint references in a given area.
Otherwise, the DSS is not in compliance with **[astm.f3548.v21.DSS0005,4](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Constraint reference removed check

If an existing constraint cannot be deleted by its manager when providing the proper ID and OVN, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005,3](../../../../requirements/astm/f3548/v21.md)**.
