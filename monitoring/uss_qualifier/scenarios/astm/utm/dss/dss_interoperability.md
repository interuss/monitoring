# ASTM F3548-21 UTM DSS interoperability test scenario

## Overview

TODO: Complete with details once we check more than the prerequisites.

This scenario currently only checks that all specified DSS instances are publicly addressable and reachable.

## Resources

### primary_dss_instance

A [resources.astm.f3548.v21.DSSInstanceResource](../../../../resources/astm/f3548/v21/dss.py) containing the "primary" DSS instance for this scenario.

### all_dss_instances

A [resources.astm.f3548.v21.DSSInstancesResource](../../../../resources/astm/f3548/v21/dss.py) containing at least two DSS instances complying with ASTM F3548-21.

### planning_area

A [resources.PlanningAreaResource](../../../../resources/planning_area.py) containing a planning area that covers the area of interest for this

### test_exclusions

A [resources.dev.TestExclusionsResource](../../../../resources/dev/test_exclusions.py) containing test exclusions parameters like whether private addresses are allowed.
This resource is optional.

## Prerequisites test case

### Test environment requirements test step

#### ⚠️ DSS instance is publicly addressable check

As per **[astm.f3548.v21.DSS0300](../../../../requirements/astm/f3548/v21.md)** the DSS instance should be publicly addressable.
As such, this check will fail if the resolved IP of the DSS host is a private IP address.
This check is skipped if the test exclusion `allow_private_addresses` is set to `True`.

#### ⚠️ DSS instance is reachable check
As per **[astm.f3548.v21.DSS0300](../../../../requirements/astm/f3548/v21.md)** the DSS instance should be publicly addressable.
As such, this check will fail if the DSS is not reachable with a dummy query.
