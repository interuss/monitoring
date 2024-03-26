# ASTM SCD DSS: Report test scenario

## Overview

This scenario tests the ability of the DSS to receive DSS reports.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

## DSS Report test case

This test attempts to submit to the DSS a report about a communication issue with a DSS that might otherwise go unnoticed.
A dummy `getOperationalIntentReference` query is made to a non-existent DSS in order to produce a realistic report, as if a DSS was not reachable when trying to retrieve an operational intent reference.

### Make valid DSS report test step

#### [Make report to DSS](../make_dss_report.md)
