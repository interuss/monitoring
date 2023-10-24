# Monitoring

This folder contains various tools to monitor, diagnose, and troubleshoot UTM
systems including DSS instances and systems that interact with DSS instances.

## Diagnostic tools

### uss_qualifier

[uss_qualifier](uss_qualifier/README.md) is an automated testing tool intended to
verify correct functionality of USSs.  For instance, one test suite verifies
correct functionality of an entire RID ecosystem by injecting known test data
into one or more RID Service Providers, observing the resulting system state via
one or more RID Display Providers, and verifying that the expected results were
observed.  It is intended to be run in a production-like shared test environment
to verify the interoperability of all participants' systems before promoting
any system changes to production.

### load_test

The [DSS load test](loadtest) sends a large number of concurrent requests to a
DSS instance to ensure it handles the load effectively.

### prober

[prober](prober) is an DSS integration test that performs a sequence of
operations on a single DSS instance and ensures that the expected results are
observed.

NOTE: `prober` is deprecated and its functionality will be migrated to uss_qualifier
scenarios.

## Mock systems

### Interoperability ecosystem

`make start-locally` (or [build/dev/run_locally.sh](../build/dev/run_locally.sh))
brings up the infrastructure for a local interoperability ecosystem including an
instance of the
[InterUSS DSS implementation](https://github.com/interuss/dss)
and a
[Dummy OAuth server](https://github.com/interuss/dss/tree/master/cmds/dummy-oauth)
which grants properly-formatted access tokens (which can be validated against the
[test public key](../build/test-certs/auth2.pem)) to anyone requesting them.

### mock_uss

[mock_uss](mock_uss) behaves like a USS for the purposes of testing and
evaluation.  It has a number of sets of functionality that can be enabled to
allow it to fulfill different roles.

## Settings

Some tools within this repository (especially uss_qualifier's report generation) need to know where on GitHub the repository is hosted.  The interuss repository URL is used by default, but this may be overridden by setting the `MONITORING_GITHUB_ROOT` environment variable.
