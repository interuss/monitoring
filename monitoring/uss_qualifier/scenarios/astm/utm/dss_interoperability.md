# ASTM F3548-21 UTM DSS interoperability test scenario

## Overview

TODO: Complete with details once we check more than the prerequisites.

This scenario currently only checks that all specified DSS instances are publicly addressable and reachable.

## Resources

### primary_dss_instance

A resources.astm.f3548.v21.DSSInstanceResource containing the "primary" DSS instance for this scenario.

### all_dss_instances

A resources.astm.f3548.v21.DSSInstancesResource containing at least two DSS instances complying with ASTM F3548-21.

## Prerequisites test case

### Test environment requirements test step

#### 🛑 DSS instance is publicly addressable check

As per **[astm.f3548.v21.DSS0300](../../../requirements/astm/f3548/v21.md)** the DSS instance should be publicly addressable.
As such, this check will fail if the resolved IP of the DSS host is a private IP address, unless that is explicitly
expected.

#### 🛑 DSS instance is reachable check
As per **[astm.f3548.v21.DSS0300](../../../requirements/astm/f3548/v21.md)** the DSS instance should be publicly addressable.
As such, this check will fail if the DSS is not reachable with a dummy query.
