# ASTM SCD DSS: Availability Arbitration test scenario

## Overview

Ensures that a DSS properly enforces limitations on created subscriptions

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

## DSS Report test case

This test attempts to submit to the DSS a report about a communication issue with a USS that might otherwise go unnoticed.
A dummy `getOperationalIntentDetails` query is made to a non-existent USS in order to produce a realistic report, as if a USS was not reachable when trying to retrieve one of its operational intent.

### Make valid DSS report test step

#### [Make report to DSS](../make_dss_report.md)


## USS Availability test case

TODO: migrate [`test_uss_availability` prober test](../../../../../prober/scd/test_uss_availability.py)
