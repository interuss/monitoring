# OVN Request Optional Extension to ASTM F3548-21 test scenario

## Description
This test validates that a DSS correctly implements the [OVN Request Optional Extension to ASTM F3548-21](../../../requirements/interuss/f3548/ovn_request.md).

## Resources

### dss
[`DSSInstanceResource`](../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

### id_generator
[`IDGeneratorResource`](../../../resources/interuss/id_generator.py) providing the base entity ID for this scenario.

### client_identity
[`ClientIdentityResource`](../../../resources/communications/client_identity.py) the client identity that will be used to create and update operational intent references.

### planning_area
[`PlanningAreaResource`](../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which operational intent references will be created.

## Setup test case

### [Ensure clean workspace test step](../../astm/utm/dss/clean_workspace.md)
This step ensures that no entities with the known test IDs exists in the DSS.

## Request for OIR OVN with valid suffix test case
This case validates the nominal behavior of the OVN request.

### Create OIR with OVN suffix request test step

#### [Create OIR with OVN suffix request](../../astm/utm/dss/fragments/oir/crud/create_query.md)
Check that the OIR creation query succeeds.

#### [DSS has set the expected OVN using the requested OVN suffix](./expected_ovn_set_fragment.md)
Check that the DSS has set the expected OVN correctly.

### Activate OIR with OVN suffix request test step

#### [Update OIR with OVN suffix request](../../astm/utm/dss/fragments/oir/crud/update_query.md)
Check that the OIR update query succeeds.

#### [DSS has set the expected OVN using the requested OVN suffix](./expected_ovn_set_fragment.md)
Check that the DSS has set the expected OVN correctly.

## Request for OIR OVN with invalid suffix test case
This case validates the off-nominal behaviors of the OVN request.

### Attempt to create OIR with OVN suffix request not being a UUID test step
#### [Attempt to create OIR with OVN suffix request not being a UUID rejected](./invalid_ovn_suffix_fragment.md)
Check that the DSS rejects OVN suffix that are not UUIDs.
If the DSS accepts the OVN suffix, or fails with an unexpected error, this check will fail.

### Attempt to create OIR with OVN suffix request empty test step
#### [Attempt to create OIR with OVN suffix request empty rejected](./invalid_ovn_suffix_fragment.md)
Check that the DSS rejects OVN suffix that are empty.
If the DSS accepts the OVN suffix, or fails with an unexpected error, this check will fail.

### Attempt to create OIR with OVN suffix request being a UUID but not v7 test step
#### [Attempt to create OIR with OVN suffix request being a UUID but not v7 rejected](./invalid_ovn_suffix_fragment.md)
Check that the DSS rejects OVN suffix that are UUIDs but not v7.
If the DSS accepts the OVN suffix, or fails with an unexpected error, this check will fail.

### Attempt to create OIR with OVN suffix request being an outdated UUIDv7 test step
#### [Attempt to create OIR with OVN suffix request being an outdated UUIDv7 rejected](./invalid_ovn_suffix_fragment.md)
Check that the DSS rejects OVN suffix that are outdated UUIDv7.
If the DSS accepts the OVN suffix, or fails with an unexpected error, this check will fail.

## [Cleanup](../../astm/utm/dss/clean_workspace.md)
