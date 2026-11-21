# ASTM SCD DSS: Operational Intent Reference Validation test scenario

## Overview

Ensures that a DSS properly validates the parameters of requests related to operational intent references.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which entities are created, modified and deleted.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the operational intent reference ID for this scenario.

### client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) the client identity that will be used to create and update operational intent references.

### planning_area

[`PlanningAreaResource`](../../../../resources/planning_area.py) describes the 3D volume in which operational intent references will be created.

### problematically_big_area

[`VolumeResource`](../../../../resources/volume.py) describing an area too big to be accepted by the DSS.

## Setup test case

### [Cleanup OIRs test step](./clean_workspace_op_intents.md)

## Creation validation test case

### Attempt creation with invalid parameters test step

This step attempts to create operational intent references with invalid parameters.

#### ⚠️ Invalid ID is rejected check

If the DSS does not reject with a 400 the creation of an operational intent reference with an ID that is not a valid UUID,
it is in violation of the OpenAPI specification referenced by **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Operational intent reference removed check

If an operational intent reference was wrongly created by one of the previous attempts, it is removed.
If it cannot be deleted when providing the proper ID and OVN, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Attempt creation with invalid extents test step

This step attempts to create operational intent references with invalid extents.

#### ⚠️ Extents not provided as a list are rejected check

If the DSS does not reject with a 400 the creation of an operational intent reference for which the extents are provided as a single volume instead of a list,
it is in violation of the OpenAPI specification referenced by **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Extents missing start time are rejected check

If the DSS does not reject with a 400 the creation of an operational intent reference for which the extents are missing their start time,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Extents missing end time are rejected check

If the DSS does not reject with a 400 the creation of an operational intent reference for which the extents are missing their end time,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Extents ending in the past are rejected check

If the DSS does not reject with a 400 the creation of an operational intent reference for which the extents end in the past,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Extents starting after they end are rejected check

If the DSS does not reject with a 400 the creation of an operational intent reference for which the extents start after they end,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Extents with invalid time format are rejected check

If the DSS does not reject with a 400 the creation of an operational intent reference for which the extents use a time format other than `RFC3339`,
it is in violation of the OpenAPI specification referenced by **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Extents with invalid coordinates are rejected check

If the DSS does not reject with a 400 the creation of an operational intent reference for which the extents contain a vertex with a latitude outside of the valid range,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Extents with a too large area are rejected check

If the DSS does not reject with a 400 or a 413 the creation of an operational intent reference for which the extents cover an area too large,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Extents with both circle and polygon outlines are rejected check

If the DSS does not reject with a 400 the creation of an operational intent reference for which the extents define both a circle and a polygon outline,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.


#### 🛑 Operational intent reference removed check

If an operational intent reference was wrongly created by one of the previous attempts, it is removed.
If it cannot be deleted when providing the proper ID and OVN, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### [Cleanup OIRs test step](./clean_workspace_op_intents_during_cleanup.md)
