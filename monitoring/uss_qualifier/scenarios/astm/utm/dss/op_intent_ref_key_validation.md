# ASTM SCD DSS: Operational Intent Reference Key Validation test scenario

## Overview

Verifies that a DSS requires from a client creating or updating operational intent references that they
provide all OVNs for all currently relevant entities.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which entities are created, modified and deleted.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the base entity ID for this scenario.

### client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) the client identity that will be used to create and update operational intent references.

### planning_area

[`PlanningAreaResource`](../../../../resources/planning_area.py) describes the 3D volume in which operational intent references will be created.

## Setup test case

### [Ensure clean workspace test step](./clean_workspace_op_intents.md)

This step ensures that no operational intent references with the known test IDs exists in the DSS.

## Key validation on creation test case

This test case will create multiple operational intent references and verify that the `key` field
of the parameters to create or update an operational intent reference is properly validated.

That is: the DSS should require that the client provides the OVNs for each entity that is in the vicinity,
both geographically and temporally, of the client's operational intent reference.

### Create first OIR test step

This step creates one operational intent references. As no other operational intent reference is present,
the `key` field may remain empty.

#### 🛑 First operational intent reference in area creation query succeeds check

With no potentially conflicting entity present, the DSS is expected to allow the creation of an operational intent without
the client specifying any OVN in the `key` field.

If the DSS rejects a well-formed request to create the operational intent reference, it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Create second non-overlapping OIR test step

This step creates a second operational intent references that does not overlap in time with the first, and
should therefore not require any entry in the `key` field.

#### 🛑 Second, non-overlapping operational intent reference creation succeeds check

With a single existing OIR in the area that is not overlapping in time, the DSS is expected to allow the creation of an operational intent without
the client specifying any OVN in the `key` field.

If the DSS rejects a well-formed request to create the operational intent reference, it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Attempt OIR creation overlapping with first OIR test step

This test step will attempt to create an operational intent reference that intersects with the first of the previously created OIR,
and expect the DSS to require its OVN to be provided in the `key` field.

This step will validate the response body for the `HTTP 409` error response from the DSS when it contains the optional `missing_operational_intents` field.

#### [Non de-conflicted request fails](fragments/oir/crud/create_conflict.md)

Checks that an attempt to create an OIR without specifying the OVN of the already existing and overlapping OIR fails.

### Attempt OIR creation overlapping with second OIR test step

This test step will attempt to create an operational intent reference that intersects with the second of the previously created OIR,
and expect the DSS to require its OVN to be provided in the `key` field.

This step will validate the response body for the `HTTP 409` error response from the DSS when it contains the optional `missing_operational_intents` field.

#### [Non de-conflicted request fails](fragments/oir/crud/create_conflict.md)

Checks that an attempt to create an OIR without specifying the OVN of the already existing and overlapping OIR fails.

### Attempt OIR creation overlapping with both OIRs test step

This test step will attempt to create an operational intent reference that intersects with both of the previously created OIRs,
and expect the DSS to require their OVNs to be provided in the `key` field.

This step will validate the response body for the `HTTP 409` error response from the DSS when it contains the optional `missing_operational_intents` field.

#### [Non de-conflicted creation request fails](fragments/oir/crud/create_conflict.md)

Checks that an attempt to create an OIR without specifying the OVNs of the already existing and overlapping OIRs fails.

### Attempt valid OIR creation overlapping with both OIRs test step

This test step will attempt to create an operational intent reference that intersects with both of the previously created OIRs,
while providing the required OVNs in the `key` field.

After this test step succeeds, three OIRs are expected to exist in the DSS, with one intersecting with the two others.

#### 🛑 Create operational intent reference with proper OVNs succeeds check

If the DSS prevents the creation of an operational intent reference that is providing all required OVNs for other entities that exist in its geo-temporal vicinity,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Key validation on mutation test case

This test case will update multiple operational intent references and verify that the `key` field
of the parameters to create or update an operational intent reference is properly validated.

That is: the DSS should require that the client provides the OVNs for each entity that is in the vicinity,
both geographically and temporally, of the client's operational intent reference.

### Attempt mutation with both OVNs missing test step

This test step will attempt to mutate the third previously created operational intent reference so that it keeps overlapping with the others,
while omitting their OVNs in the `key` field.

The expectation is that the DSS will require the two missing OVNs.

#### [Non de-conflicted mutation request fails](fragments/oir/crud/update_conflict.md)

### Attempt mutation with first OVN missing test step

This test step will attempt to mutate the third previously created operational intent reference so that it keeps overlapping with the others,
while omitting the first OVN in the `key` field.

The expectation is that the DSS will require the missing OVN.

#### [Non de-conflicted mutation request fails](fragments/oir/crud/update_conflict.md)

### Attempt mutation to overlap with the first OIR test step

This test step will attempt to mutate the third previously created operational intent reference so that it overlaps with the first one,
while omitting the first OVN in the `key` field.

The expectation is that the DSS will require the missing OVN.

#### [Non de-conflicted mutation request fails](fragments/oir/crud/update_conflict.md)

## [Cleanup](./clean_workspace_op_intents.md)
