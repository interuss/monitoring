# ASTM SCD DSS: OIR circle overlap test scenario

## Overview

Tests the DSS operational intent reference search API when a small query circle
overlaps a larger registered circle close to its boundary. This is an HTTP-level
regression for the false negative fixed in interuss/dss#1914.

The scenario places four circular references relative to the configured
PlanningAreaResource, without requiring Kentland GPS coordinates. Each reference
is searched with four overlapping 1 m circles near its boundary; other queries
verify horizontal separation, altitude, time, and ordinary overlap.

The four geometry patterns were checked against the actual old 20-gon S2
covering and the fixed S2 Cap covering in five translated planning areas.
At least one boundary query reproduces the old false negative in each area.
The test requires sufficient horizontal room for its circles and controls;
areas that are too small fail explicitly rather than silently passing.
A geographical setting not covered by those five research areas is still
tested for correct behavior, but a failure of the old code is not guaranteed.

## Resources

### dss

A DSS instance with ASTM F3548-21 Strategic Coordination permission, used to
create, search, and delete operational intent references.

### id_generator

An `IDGeneratorResource` supplying a dedicated test OIR ID.

### planning_area

A `PlanningAreaResource` used to place the test circles inside the current
DSS test environment.

## Setup test case

### Clear previous test OIR test step

Remove an OIR left by a previous run, if it exists.

#### 🛑 Operational intent references can be queried by ID check

Retrieving an OIR by ID must succeed or return 404 when absent;
otherwise **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)** is violated.

#### 🛑 Operational intent reference removed check

A test-owned OIR must be removable by ID and correct OVN under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Discover an OIR through an overlapping circle test case

### Create large circular OIR test step

Create an accepted circular OIR (700–1,100 m radius) with matching time
and altitude bounds. Repeat for each of the four relative geometry patterns.

#### 🛑 Create operational intent reference query succeeds check

Valid OIR creation must succeed under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Boundary overlap is discoverable test step

Four 1 m circles overlapping the boundary of the registered circle must
each find the OIR. The time and altitude intervals also overlap.

#### 🛑 Boundary overlap is discoverable check

The reference's presence must match the 4D query expectation under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Distant circle does not match test step

A geographically distant query is separated from the reference and must not return the OIR.

#### 🛑 Distant circle does not match check

The reference's presence must match the 4D query expectation under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Disjoint altitude does not match test step

A horizontally overlapping query above the OIR's altitude range must not return the OIR.

#### 🛑 Disjoint altitude does not match check

The reference's presence must match the 4D query expectation under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Disjoint time does not match test step

A horizontally and vertically overlapping query entirely after the OIR's time range must not return the OIR.

#### 🛑 Disjoint time does not match check

The reference's presence must match the 4D query expectation under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Ordinary contained circle is discoverable test step

An ordinary 200 m circle contained well inside the registered OIR must be found.

#### 🛑 Ordinary contained circle is discoverable check

The reference's presence must match the 4D query expectation under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Delete large circular OIR test step

Remove the created OIR after the search.

#### 🛑 Delete operational intent reference query succeeds check

Deleting a test-owned OIR with the correct OVN must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### Clean up test OIR test step

Remove the known OIR ID on failure or early termination.

#### ⚠️ Operational intent references can be queried by ID check

The DSS should return the reference or 404 for an absent reference
under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Operational intent reference removed check

A test-owned OIR must be removable using the correct OVN under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.
