# Validate GET interaction test step fragment

This step verifies that a USS makes a GET request to get the intent_details of an existing operation when needed as per ASTM F3548-21 by checking the interuss interactions of mock uss

## 🛑 MockUSS interactions request check
**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.

## 🛑 Expect GET request when no notification check
**[astm.f3548.v21.SCD0035](../../../../../requirements/astm/f3548/v21.md)**
SCD0035 needs a USS to verify before transitioning to Accepted that it does not conflict with a type of operational intent, and the only way to have verified this is by knowing all operational intent details, and (from previous checks of no notifications) the only way to know the operational intent details of flight is to have requested them via a GET details interaction.
