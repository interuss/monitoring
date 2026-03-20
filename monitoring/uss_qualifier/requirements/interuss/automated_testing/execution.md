# InterUSS automated test execution requirements

## Requirements

### <tt>RunToCompletion</tt>

When a test configuration designer specifies that an automated test must run to completion (by including this requirement), all applicable participants in the automated test will fail this requirement if the automated test does not run to completion.  Not running to completion may be due to exceeding the maximum allowed test run time in ExecutionConfiguration.stop_after or because of a failed check with Critical severity.
