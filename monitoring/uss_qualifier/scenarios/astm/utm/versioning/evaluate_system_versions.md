# ASTM F3548-21 evaluate system versions test scenario

## Overview

ASTM F3548-21 GEN0305 requires that the USS's test system (provided per GEN0300) uses the currently deployed software version except when testing an update.  This scenario checks the test and production versions of all participants' systems and ensures that no more than one participant's test system (presumably the participant who is testing an update) has a different version than their production system.

## Resources

### test_env_version_providers

A [`VersionProvidersResource`](../../../../resources/versioning/client.py) containing the means by which to query test-environment system versions for each applicable participant.

### prod_env_version_providers

A [`VersionProvidersResource`](../../../../resources/versioning/client.py) containing the means by which to query production-environment system versions for each applicable participant.

### system_identity

A [`SystemIdentityResource`](../../../../resources/versioning/system_identity.py) indicating the identity of the system for which to query the version from all providers.

## Evaluate versions test case

### Get test environment test versions test step

Each version provider is queried for the version of its system (identified by system_identity) in the test environment.

#### ⚠️ Valid response check

If a valid response is not received from a version provider, they will have failed to meet **[versioning.ReportSystemVersion](../../../../requirements/versioning.md)**.

### Get production environment versions test step

Each version provider is queried for the version of its system (identified by system_identity) in the production environment.

#### ⚠️ Valid response check

If a valid response is not received from a version provider, they will have failed to meet **[versioning.ReportSystemVersion](../../../../requirements/versioning.md)**.

### Evaluate current system versions test step

#### ⚠️ At most one participant is testing a new software version check

Per GEN0305, a participant may temporarily have a different software version in the test environment than in production in order to test that new software version.  But, as the purpose of testing is to ensure continued compliance and interoperation with other participants' systems that have already been demonstrated functional, if two or more participants have differing software versions between the test and production environments, at least one of these participants will have failed to meet **[astm.f3548.v21.GEN0305](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Test software version matches production check

For participants not testing a new software version, their test-environment software version must match their production-environment software version or that participant does not meet **[astm.f3548.v21.GEN0305](../../../../requirements/astm/f3548/v21.md)**.

### Evaluate system version consistency test step

#### ⚠️ Software versions are consistent throughout test run check

If the system version reported by a participant at one point during the test run is different from the system version reported by that participant at a different point during the test run, that participant cannot meet **[astm.f3548.v21.GEN0305](../../../../requirements/astm/f3548/v21.md)** because the test environment and production environment system versions cannot be compared because the version in at least one of those environments does not have a consistent value.
