# ASTM SCD DSS: Interfaces authentication test scenario

## Overview

Ensures that a DSS properly authenticates requests to all its endpoints.

Note that this does not cover authorization.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

Note that to benefit from the maximum coverage, the DSS' AuthAdapterResource must be able to obtain credentials
for multiple scopes (so that a wrong scope may be used in place of the correct one) as well as an empty scope
(that is, provide credentials where the scope is an empty string).

This scenario will check for the scope's availability and transparently ignore checks that can't be conducted.

At least one of the following scopes needs to be available for this scenario to at least partially run:

- `utm.strategic_coordination`
- `utm.availability_arbitration`
- `utm.constraint_management`

In order to verify each endpoint group, all scopes above must be available.

Optional scopes that will allow the scenario to provide additional coverage:

- `""` (empty string)

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the Subscription ID for this scenario.

### planning_area

[`PlanningAreaResource`](../../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which entities will be created.

## Setup test case

### [Ensure clean workspace test step](../clean_workspace.md)

This step ensures that the availability for the test identifier is set to `Unknown`.

#### [Availability can be requested](../fragments/availability/read.md)

#### [Availability can be set](../fragments/availability/update.md)

## Endpoint authorization test case

This test case ensures that the DSS properly authenticates requests to all its endpoints.

### Subscription endpoints authentication test step

#### 🛑 Unauthorized requests return the proper error message body check

If the DSS under test does not return a proper error message body when an unauthorized request is received, it fails to properly implement the OpenAPI specification that is part of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create subscription with missing credentials check

If the DSS under test allows the creation of a subscription without any credentials being presented, it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create subscription with invalid credentials check

If the DSS under test allows the creation of a subscription with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create subscription with missing scope check

If the DSS under test allows the creation of a subscription with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create subscription with incorrect scope check

If the DSS under test allows the creation of a subscription with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create subscription with valid credentials check

If the DSS does not allow the creation of a subscription when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get subscription with missing credentials check

If the DSS under test allows the fetching of a subscription without any credentials being presented, it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get subscription with invalid credentials check

If the DSS under test allows the fetching of a subscription with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get subscription with missing scope check

If the DSS under test allows the fetching of a subscription with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get subscription with incorrect scope check

If the DSS under test allows the fetching of a subscription with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get subscription with valid credentials check

If the DSS does not allow fetching a subscription when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate subscription with missing credentials check

If the DSS under test allows the mutation of a subscription without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate subscription with invalid credentials check

If the DSS under test allows the mutation of a subscription with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate subscription with missing scope check

If the DSS under test allows the mutation of a subscription with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate subscription with incorrect scope check

If the DSS under test allows the mutation of a subscription with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate subscription with valid credentials check

If the DSS does not allow the mutation of a subscription when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete subscription with missing credentials check

If the DSS under test allows the deletion of a subscription without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete subscription with invalid credentials check

If the DSS under test allows the deletion of a subscription with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete subscription with missing scope check

If the DSS under test allows the deletion of a subscription with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete subscription with incorrect scope check

If the DSS under test allows the deletion of a subscription with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete subscription with valid credentials check

If the DSS does not allow the deletion of a subscription when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search subscriptions with missing credentials check

If the DSS under test allows searching for subscriptions without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search subscriptions with invalid credentials check

If the DSS under test allows searching for subscriptions with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search subscriptions with missing scope check

If the DSS under test allows searching for subscriptions with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search subscriptions with incorrect scope check

If the DSS under test allows searching for subscriptions with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search subscriptions with valid credentials check

If the DSS does not allow searching for subscriptions when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

### Operational intents endpoints authentication test step

#### 🛑 Unauthorized requests return the proper error message body check

If the DSS under test does not return a proper error message body when an unauthorized request is received,
it fails to properly implement the OpenAPI specification that is part of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create operational intent reference with missing credentials check

If the DSS under test allows the creation of an operational intent without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create operational intent reference with invalid credentials check

If the DSS under test allows the creation of an operational intent with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create operational intent reference with missing scope check

If the DSS under test allows the creation of an operational intent with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create operational intent reference with incorrect scope check

If the DSS under test allows the creation of an operational intent with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create operational intent reference with valid credentials check

If the DSS does not allow the creation of an operational intent when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

#### [Create response format](../fragments/oir/crud/create_format.md)

Check response format of a creation request.

#### 🛑 Get operational intent reference with missing credentials check

If the DSS under test allows the fetching of an operational intent without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get operational intent reference with invalid credentials check

If the DSS under test allows the fetching of an operational intent with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get operational intent reference with missing scope check

If the DSS under test allows the fetching of an operational intent with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get operational intent reference with incorrect scope check

If the DSS under test allows the fetching of an operational intent with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get operational intent reference with valid credentials check

If the DSS does not allow fetching an operational intent when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate operational intent reference with missing credentials check

If the DSS under test allows the mutation of an operational intent without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate operational intent reference with invalid credentials check

If the DSS under test allows the mutation of an operational intent with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate operational intent reference with missing scope check

If the DSS under test allows the mutation of an operational intent with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate operational intent reference with incorrect scope check

If the DSS under test allows the mutation of an operational intent with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate operational intent reference with valid credentials check

If the DSS does not allow the mutation of an operational intent when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

#### [Mutate response format](../fragments/oir/crud/update_format.md)

Check response format of a mutation.

#### 🛑 Delete operational intent reference with missing credentials check

If the DSS under test allows the deletion of an operational intent without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete operational intent reference with invalid credentials check

If the DSS under test allows the deletion of an operational intent with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete operational intent reference with missing scope check

If the DSS under test allows the deletion of an operational intent with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete operational intent reference with incorrect scope check

If the DSS under test allows the deletion of an operational intent with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete operational intent reference with valid credentials check

If the DSS does not allow the deletion of an operational intent when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search operational intent references with missing credentials check

If the DSS under test allows searching for operational intents without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search operational intent references with invalid credentials check

If the DSS under test allows searching for operational intents with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search operational intent references with missing scope check

If the DSS under test allows searching for operational intents with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search operational intent references with incorrect scope check

If the DSS under test allows searching for operational intents with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search operational intent references with valid credentials check

If the DSS does not allow searching for operational intents when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

### Availability endpoints authentication test step

#### 🛑 Unauthorized requests return the proper error message body check

If the DSS under test does not return a proper error message body when an unauthorized request is received,
it fails to properly implement the OpenAPI specification that is part of **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Read availability with missing credentials check

If the DSS under test allows the fetching of a USS's availability without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Read availability with invalid credentials check

If the DSS under test allows the fetching of a USS's availability with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Read availability with missing scope check

If the DSS under test allows the fetching of a USS's availability with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Read availability with incorrect scope check

If the DSS under test allows the fetching of a USS's availability with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Read availability with valid credentials check

If the DSS does not allow fetching a USS's availability when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 USS Availability Get response format conforms to spec check

The response to a successful USS Availability request is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21,
otherwise, the DSS is failing to implement **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Set availability with missing credentials check

If the DSS under test allows the setting of a USS's availability without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Set availability with invalid credentials check

If the DSS under test allows the setting of a USS's availability with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Set availability with missing scope check

If the DSS under test allows the setting of a USS's availability with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Set availability with incorrect scope check

If the DSS under test allows the setting of a USS's availability with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Set availability with valid credentials check

If the DSS does not allow setting a USS's availability when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 USS Availability Set response format conforms to spec check

The response to a successful USS Availability Set request is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21,
otherwise, the DSS is failing to implement **[astm.f3548.v21.DSS0100,1](../../../../../requirements/astm/f3548/v21.md)**.

### Constraint reference endpoints authentication test step

#### 🛑 Unauthorized requests return the proper error message body check

If the DSS under test does not return a proper error message body when an unauthorized request is received,
it fails to properly implement the OpenAPI specification that is part of **[astm.f3548.v21.DSS0005,3](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create constraint reference with missing credentials check

If the DSS under test allows the creation of a constraint reference without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create constraint reference with invalid credentials check

If the DSS under test allows the creation of a constraint reference with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create constraint reference with missing scope check

If the DSS under test allows the creation of a constraint reference with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create constraint reference with incorrect scope check

If the DSS under test allows the creation of a constraint reference with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Create constraint reference with valid credentials check

If the DSS does not allow the creation of a constraint reference when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

#### [Create response format](../fragments/cr/crud/create_format.md)

Check response format of a creation request.

#### 🛑 Get constraint reference with missing credentials check

If the DSS under test allows the fetching of a constraint reference without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get constraint reference with invalid credentials check

If the DSS under test allows the fetching of a constraint reference with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get constraint reference with missing scope check

If the DSS under test allows the fetching of a constraint reference with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get constraint reference with incorrect scope check

If the DSS under test allows the fetching of a constraint reference with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get constraint reference with valid credentials check

If the DSS does not allow fetching a constraint reference when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate constraint reference with missing credentials check

If the DSS under test allows the mutation of a constraint reference without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate constraint reference with invalid credentials check

If the DSS under test allows the mutation of a constraint reference with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate constraint reference with missing scope check

If the DSS under test allows the mutation of a constraint reference with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate constraint reference with incorrect scope check

If the DSS under test allows the mutation of a constraint reference with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate constraint reference with valid credentials check

If the DSS does not allow the mutation of a constraint reference when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

#### [Mutate response format](../fragments/cr/crud/update_format.md)

Check response format of a mutation.

#### 🛑 Delete constraint reference with missing credentials check

If the DSS under test allows the deletion of a constraint reference without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete constraint reference with invalid credentials check

If the DSS under test allows the deletion of a constraint reference with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete constraint reference with missing scope check

If the DSS under test allows the deletion of a constraint reference with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete constraint reference with incorrect scope check

If the DSS under test allows the deletion of a constraint reference with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete constraint reference with valid credentials check

If the DSS does not allow the deletion of a constraint reference when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search constraint references with missing credentials check

If the DSS under test allows searching for constraint references without any credentials being presented,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search constraint references with invalid credentials check

If the DSS under test allows searching for constraint references with credentials that are well-formed but invalid,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search constraint references with missing scope check

If the DSS under test allows searching for constraint references with valid credentials but a missing scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search constraint references with incorrect scope check

If the DSS under test allows searching for constraint references with valid credentials but an incorrect scope,
it is in violation of **[astm.f3548.v21.DSS0210,A2-7-2,7](../../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search constraint references with valid credentials check

If the DSS does not allow searching for constraint references when valid credentials are presented,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../requirements/astm/f3548/v21.md)**.

## [Cleanup](../clean_workspace.md)

### [Availability can be requested](../fragments/availability/read.md)

### [Availability can be set](../fragments/availability/update.md)

The cleanup phase of this test scenario removes the subscription with the known test ID if it has not been removed before.
