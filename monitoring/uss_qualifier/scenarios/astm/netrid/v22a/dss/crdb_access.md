# ASTM NetRID DSS: Direct CRDB access test scenario

## Overview

Attempt to directly access the CockroachDB (CRDB) nodes intercommunicating to form the DSS Airspace Representation for the DSS instances under test, for the purpose of determining compliance to certain DSS interoperability requirements.

Note that none of this scenario is implemented yet.

## Resources

## Future resources

### crdb_nodes

Set of CockroachDB nodes constituting the DSS instances under test.

TODO: Create this resource

## Verify security interoperability test case

### Attempt unauthorized access test step

In this test step, uss_qualifier attempts to connect to each CRDB node in insecure mode.

#### CRDB node in insecure mode check

If connection to a CRDB node in insecure mode succeeds, the USS will have failed to authenticate clients per **[astm.f3411.v22a.DSS0110](../../../../../requirements/astm/f3411/v22a.md)**.

TODO: Implement this step and check

### Verify encryption test step

This step verifies the use of TLS for every CRDB node specified.

#### TLS in use check

If a CRDB node does not have TLS in use, the test will have failed to verify the encryption requirement **[astm.f3411.v22a.DSS0120](../../../../../requirements/astm/f3411/v22a.md)**.

TODO: Implement this step and check
