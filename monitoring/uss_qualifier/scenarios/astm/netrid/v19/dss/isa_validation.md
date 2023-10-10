# ASTM NetRID DSS: Submitted ISA Validations test scenario

## Overview

Perform basic operations on a single DSS instance to create an ISA and query it during its time of applicability and
after its time of applicability.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the ISA ID for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing an ISA to be created.

### problematically_big_area

[`VerticesResource`](../../../../../resources/vertices.py) describing an area designed to be too big to be accepted by the DSS.

## Setup test case

### Ensure clean workspace test step

This scenario creates an ISA with a known ID.  This step ensures that ISA does not exist before the start of the main
part of the test.

#### Successful ISA query check

**[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

#### Removed pre-existing ISA check

If an ISA with the intended ID is already present in the DSS, it needs to be removed before proceeding with the test.  If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Notified subscriber check

When a pre-existing ISA needs to be deleted to ensure a clean workspace, any subscribers to ISAs in that area must be notified (as specified by the DSS).  If a notification cannot be delivered, then the **[astm.f3411.v19.NET0710](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the POST ISAs endpoint isn't met.


## ISA Validation test case

### ISA Validation test step

#### ISA huge area check

Attempting to put a too large ISA should result in a 400.

#### ISA empty vertices check

An ISA with a empty `vertices` array in the `extents.spatial_volume.footprint` field of the ISA creation payload should not result in a successful submission.

#### ISA start time in the past check

The DSS must reject ISAs with start times in the past.

#### ISA start time after end time check

The DSS must reject ISAs for which the start time is after the end time.

#### ISA vertices are valid check

The DSS must reject ISAs with invalid vertices, such as vertices that have latitude or longitude outside meaningful ranges.

#### ISA missing outline check

If the outline polygon is missing from the `extents.spatial_volume.footprint` field in the payload of the ISA creation request,
the DSS is expected to reject the request.

#### ISA missing volume check

If the outline polygon is missing from the `extents.spatial_volume` field in the payload of the ISA creation request,
the DSS is expected to reject the request.

#### ISA missing extents check

If the `extents` field is missing from the payload of the ISA creation request,
the DSS is expected to reject the request.

## Cleanup

The cleanup phase of this test scenario attempts to remove the ISA if the test ended prematurely.

### Successful ISA query check

**[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

### Removed pre-existing ISA check

If an ISA with the intended ID is still present in the DSS, it needs to be removed before exiting the test. If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

### Notified subscriber check

When an ISA is deleted, subscribers must be notified. If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v19.NET0730](../../../../../requirements/astm/f3411/v19.md)**.
