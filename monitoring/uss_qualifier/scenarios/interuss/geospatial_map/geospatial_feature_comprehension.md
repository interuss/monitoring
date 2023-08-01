# Geospatial feature comprehension test scenario

## Description

This test acts as a user viewing a USS's geospatial map and queries areas and features of interest according to the Feature Check Table provided by the test designer (see `table` resource below), expecting relevant features to be present or absent according to the test designer.  For instance, the test designer may include a Feature Check in their Feature Check table which causes this test to query for geospatial features that would block flight planning in an area of known restrictions and expect matching features to be found there.  But, when a similar query is performed in an area that is known to be free of restrictions, this test would be expected to find no matching features there.  More information may be seen [here](https://github.com/interuss/tsc/pull/7).

## Resources

### table

[Feature Check Table](../../../resources/interuss/geospatial_map/feature_check_table.py) consisting of a list of Feature Check rows.  Each Feature Check row will cause this test to query the geospatial map of each USS under test according to the information in that Feature Check row.  This test will then perform checks according to the expected outcomes from those queries, according to the Feature Check row.

## Map query test case

### Dynamic test step

The test steps for this test scenario are generated dynamically according to the definitions in the Feature Check Table.  The checks for each step are the same and are documented below.

#### Blocking geospatial features present check

When the test designer specifies that a particular Feature Check has an expected result of "Block", that means querying a USS for geospatial features that would result in blocking a flight with the other specified characteristics should find matching geospatial features.  Upon performing this query, if this test finds no such matching geospatial features, this check will fail.

#### Advisory geospatial features present check

When the test designer specifies that a particular Feature Check has an expected result of "Advise", that means querying a USS for geospatial features that would result in advisories or conditions for a flight with the other specified characteristics should find matching geospatial features.  Upon performing this query, if the test finds no such matching geospatial features, this check will fail.

#### No blocking or advisory features present

When the test designer specifies that a particular Feature Check has an expected result of "Neither" (neither Block nor Advise), that means querying a USS for geospatial features that would result in blocking or producing advisories or conditions for a flight with the other specified characteristics should find no matching geospatial features.  Upon performing this query, if the test finds any such matching geospatial features, this check will fail.
