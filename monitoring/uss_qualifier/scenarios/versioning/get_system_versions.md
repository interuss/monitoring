# Get system versions test scenario

This test scenario obtains versions for the specified systems.

## Resources

### version_providers

A [`VersionProvidersResource`](../../resources/versioning/client.py) containing the means by which to query system versions for each applicable participant.

### system_identity

A [`SystemIdentityResource`](../../resources/versioning/system_identity.py) indicating the identity of the system for which to query the version from all providers.

## Get versions test case

### Get versions test step

Each version provider is queried for the version of its system (identified by system_identity) and the result is recorded as a note in the report.

#### Valid response check

If a valid response is not received from a version provider, they will have failed to meet **[versioning.ReportSystemVersion](../../requirements/versioning.md)**.
