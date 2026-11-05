# InterUSS DSS aux interface test scenario

## Overview

This scenario verifies that a DSS instance exposes the InterUSS-defined `aux` interface and responds correctly to queries on it.

## Resources

### dss

[`DSSInstanceResource`](../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

## Version test case

### Query version test step

The DSS instance is queried for its version at `/aux/v1/version`.

#### ⚠️ Version can be queried check

If the DSS instance does not respond with a valid version response, the USS hosting it does not comply with **[interuss.dss.hosting.ExposeAux](../../../requirements/interuss/dss/hosting.md)**.

#### ⚠️ Version is defined check

If the version reported by the DSS instance is empty or contains `undefined`, the DSS instance was not built with a proper version and the USS hosting it does not comply with **[interuss.dss.hosting.ExposeAux](../../../requirements/interuss/dss/hosting.md)**.
