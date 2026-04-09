# DSS pool information test scenario

This test scenario obtains and validates information about any InterUSS ASTM F3548-21 DSS instances in a pool of interest.

## Resources

### dss_instances

A [`DSSInstancesResource`](../../resources/astm/f3548/v21/dss.py) containing all instances of interest within a single pool.  Not all instances must be InterUSS implementations, but only instances which are sufficiently-recent InterUSS implementations are likely to produce useful information and validation.

The auth adapter for each DSS instance must support uss_qualifier's acquisition of access tokens with the `interuss.pool_status.read` scope.

## aux information test case

Information available via the InterUSS DSS implementation's aux interface is queried and noted and/or evaluated when obtained.

### Examine versions test step

Each DSS instance is queried for its version at `/aux/v1/version` and the versions are noted for the report.

#### ⚠️ Version obtained successfully check

If uss_qualifier cannot successfully obtain version information, the USS hosting the queried DSS instance does not comply with **[interuss.dss.hosting.ExposeAux](../../../../requirements/interuss/dss/hosting.md)**.

TODO: Implement

### Examine pool test step

Each DSS instance is queried for its understanding of the pool at `/aux/v1/pool`.

#### ⚠️ Pool information obtained successfully check

If uss_qualifier cannot successfully obtain pool information, the USS hosting the queried DSS instance does not comply with **[interuss.dss.hosting.ExposeAux](../../../../requirements/interuss/dss/hosting.md)**.

TODO: Implement

#### ⚠️ DAR ID matches check

If any two DSS instances who successfully reported their DAR ID in the pool information have differeing DAR IDs, those DSS instances are not part of the same pool and have therefore failed to comply with **[astm.f3548.v21.DSS0020](../../../../requirements/astm/f3548/v21.md)**.

TODO: Implement

### Examine DSS instances test step

Each DSS instance is queried for its understanding of the other instances in the pool at `/aux/v1/pool/dss_instances`.

#### ⚠️ DSS instances obtained successfully check

If uss_qualifier cannot successfully obtain the pool's DSS instance information from the queried DSS, the USS hosting the DSS instance does not comply with **[interuss.dss.hosting.ExposeAux](../../../../requirements/interuss/dss/hosting.md)**.

TODO: Implement

#### ⚠️ DSS instances have same understanding of other instances check

If any two DSS instances differ in what DSS instances they believe are part of the pool, then those two instances are not successfully reading a shared repository of pool information.  In the InterUSS implementation, this means they have failed to comply with **[astm.f3548.v21.DSS0020](../../../../requirements/astm/f3548/v21.md)** because reading from a shared repository of information is what achieves DSS0020 compliance in InterUSS DSS implementations.

A difference in any element of the DSSInstances information (e.g., instance ID, public endpoint) may cause this check to fail, but uss_qualifier attempts to avoid false positives when a new heartbeat arrives in between instance polling.

TODO: Implement

### Examine CA certificates test step

Each DSS instance is queried for the CA certificates used to sign its node certificates (via `/aux/v1/configuration/ca_certs`) and also the CA certificates it accepts (via `/aux/v1/configuration/accepted_ca_certs`).

#### ⚠️ CA certs obtained successfully check

If uss_qualifier cannot successfully obtain CA certificate information, the USS hosting the queried DSS instance does not comply with **[interuss.dss.hosting.ExposeAux](../../../../requirements/interuss/dss/hosting.md)**.

TODO: Implement

#### ⚠️ DSS instance accepts all pool CA certs check

If a DSS instance does not accept any of the CA certificates used to sign the node certificates of any other DSS instance in the pool, the USS hosting that DSS instance will not comply with **[astm.f3548.v21.DSS0020](../../../../requirements/astm/f3548/v21.md)** because the InterUSS DSS implementation relies on every DSS instance accepting the certificates of every other DSS instance in the pool to comply with this requirement.

TODO: Implement
