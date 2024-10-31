# Validate operational intent details obtained test step fragment
This step verifies that a USS obtained operational intent details from a Mock USS by means of either a notification from
the Mock USS (push), or a GET request (operation *getOperationalIntentDetails*) to the Mock USS.

## [Get Mock USS interactions logs](../../../../interuss/mock_uss/get_mock_uss_interactions.md)

## 🛑 USS obtained operational intent details by means of either notification or GET request check
SCD0035 requires a USS to verify before transitioning to Accepted that it does not conflict with another operational
intent, and the only way to have verified this is by knowing all operational intent details.
As such, if the USS was neither notified of the details by the Mock USS, nor did it retrieve them directly from the Mock
USS, this check will fail per **[astm.f3548.v21.SCD0035](../../../../../requirements/astm/f3548/v21.md)**
