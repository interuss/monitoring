# ASTM F3548-21 UTM DSS Operational Intent Access Control test scenario

## Overview

This scenario ensures that a DSS will only let the owner of an operational intent modify it.

## Resources

### flight_intents

A `resources.flight_planning.FlightIntentsResource` containing the flight intents to be used in this scenario:

This scenario expects to find at least two separate flight intents in this resource, as it will use their extent
to create two operational intents.

### dss

A `resources.astm.f3548.v21.DSSInstanceResource` pointing to the DSS instance to test for this scenario.

### second_utm_auth

A `resources.communications.AuthAdapterResource` containing a second set of valid credentials for interacting with the DSS.

This second set of credentials is required to validate that the DSS is properly enforcing access control rules, and properly limits the actions of a client against
the resources exposed by the DSS.

The participant under test is responsible for providing this second set of credentials along the primary ones used in most other scenarios.

#### Credential requirements

In general, these test credentials may be in all points equal to the ones used by the `AuthAdapterResource` that is
provided to the `dss` resources above, except for the value contained in the `sub` claim of the token.

For the purpose of this scenario, these credentials must be allowed to create, modify and delete operational intents on the DSS,
as well as querying operational intent references.

##### Required scope

For the purpose of this scenario, the `second_utm_auth` resource must provide access to a token with at least the following scope:

* `utm.strategic_coordination`

##### Separate subscription

Note that the subscription (or 'sub' claim) of the token that will be obtained for this resource
MUST be different from the one of the `dss` resources mentioned above:
this will be verified at runtime, and this scenario will fail if the second set of credentials belong to the same subscription as the main one.

### id_generator

A `resources.interuss.IDGeneratorResource` that will be used to generate the IDs of the operational intents created in this scenario.

## Setup test case

Makes sure that the DSS is in a clean and expected state before running the test, and that the passed resources work as required.

The setup will create two separate operational intents: one for each set of the available credentials.

### Ensure clean workspace test step

#### Operational intents can be queried directly by their ID check

If an existing operational intent cannot directly be queried by its ID, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**.

#### Operational intents can be searched using valid credentials check

A client with valid credentials should be allowed to search for operational intents in a given area.
Otherwise, the DSS is not in compliance with **[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**.

#### Operational intents can be deleted by their owner check

If an existing operational intent cannot be deleted when providing the proper ID and OVN, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**.

### Create operational intents with different credentials test step

This test step ensures that an operation intent created with the main credentials is available for the main test case.

To verify that the second credentials are valid, it will also create an operational intent with those credentials.

#### Can create an operational intent with valid credentials check

If the DSS does not allow the creation of operation intents when the required parameters and credentials are provided,
it is in violation of **[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**.

#### Passed sets of credentials are different check

This scenario requires two sets of credentials that have a different 'sub' claim in order to validate that the
DSS properly controls access to operational intents.

## Attempt unauthorized flight intent modification test case

This test case ensures that the DSS does not allow a caller to modify or delete operational intent that they did not create.

### Attempt unauthorized flight intent modification test step

This test step will attempt to modify the operational intent that was created using the configured `dss` resource,
using the credentials provided in the `second_utm_auth` resource, and expect all such attempts to fail.

#### Operational intents can be queried directly by their ID check

If an existing operational intent cannot directly be queried by its ID, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**.

#### Non-owning credentials cannot modify operational intent check

If an operational intent can be modified by a client which did not create it, the DSS implementation is
in violation of **[astm.f3548.v21.OPIN0035](../../../requirements/astm/f3548/v21.md)**.

#### Non-owning credentials cannot delete operational intent check

If an operational intent can be deleted by a client which did not create it, the DSS implementation is
in violation of **[astm.f3548.v21.OPIN0035](../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### Operational intents can be queried directly by their ID check

If an existing operational intent cannot directly be queried by its ID, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**.

### Operational intents can be deleted by their owner check

If an existing operational intent cannot be deleted when providing the proper ID and OVN, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005](../../../requirements/astm/f3548/v21.md)**.
