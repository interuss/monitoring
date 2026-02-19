# Tested requirements artifact

## Purpose

A tested requirements artifact is intended to group test checks performed
for a given participant by the requirement they were measuring.  In this way,
the means of measurement of compliance for each requirement can be easily
identified, including cases where compliance was not measured for
requirements of interest.

## Participant pages

Each participant's page summarizes the test run and then lists all test
checks performed for that participant, ordered by relevant requirement.  The
list of relevant requirements included on this page can either be set
explicitly in the artifact configuration, or else it defaults to every
requirement that the set of scenarios run may have been capable of measuring.

### Requirement summaries

Each requirement is summarized (see [`TestedRequirement.status`](./data_types.py)) for a participant in the following way:

<table>
  <thead>
    <tr>
      <th rowspan="3">Requirement status</th>
      <th rowspan="3">Meaning</th>
      <th colspan="5">Criteria for checks associated with the requirement</th>
    </tr>
    <tr>
      <th rowspan="2">Pass</th>
      <th rowspan="2">Not tested</th>
      <th colspan="3">Fail</th>
    </tr>
    <tr>
      <th>Medium+ severity, not in <code>acceptable_&#8203;findings</code></th>
      <th>Low severity, not in <code>acceptable_&#8203;findings</code></th>
      <th>In <code>acceptable_&#8203;findings</code></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Fail</td>
      <td>The participant is likely to be non-compliant with one or more requirements</td>
      <td>Any number</td>
      <td>Any number</td>
      <td>At least one</td>
      <td>Any number</td>
      <td>Any number</td>
    </tr>
    <tr>
      <td>Findings</td>
      <td>The participant was not detected as non-compliant to any requirement, but there are important findings and no fully-successful checks</td>
      <td>None</td>
      <td>Any number</td>
      <td>None</td>
      <td>At least one</td>
      <td>Any number</td>
    </tr>
    <tr>
      <td>Pass (with findings)</td>
      <td>The participant was not detected as non-compliant to any requirement, and some checks validate compliance to the requirement, but there are important findings</td>
      <td>At least one</td>
      <td>Any number</td>
      <td>None</td>
      <td>At least one</td>
      <td>Any number</td>
    </tr>
    <tr>
      <td>Pass</td>
      <td>At least one test check measuring compliance with the requirement did not detect non-compliance, and no non-compliance was detected</td>
      <td>At least one</td>
      <td>Any number</td>
      <td>None</td>
      <td>None</td>
      <td>Any number</td>
    </tr>
    <tr>
      <td>Not tested</td>
      <td>No checks associated with the requirement produced positive or negative results</td>
      <td>None</td>
      <td>Any number</td>
      <td>None</td>
      <td>None</td>
      <td>Any number</td>
    </tr>
  </tbody>
</table>

### Top-level verification status

The overall "Requirement verification status" for the participant is
summarized in the following way (see [`compute_overall_status`](./summaries.py)):

<table>
  <thead>
    <tr>
      <th rowspan="2">Verification status (top-level)</th>
      <th rowspan="2">Meaning</th>
      <th colspan="4">Criteria for requirements included in the artifact</th>
    </tr>
    <tr>
      <th>Fail</th>
      <th>Findings</th>
      <th>Pass (with findings)</th>
      <th>Pass</th>
      <th>Not tested</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Fail</td>
      <td>The participant is likely to be non-compliant with one or more relevant requirements</td>
      <td>At least one</td>
      <td>Any number</td>
      <td>Any number</td>
      <td>Any number</td>
      <td>Any number</td>
    </tr>
    <tr>
      <td>Pass</td>
      <td>Every requirement considered relevant for the artifact has at least one test check measuring the participant's compliance with the requirement, and no relevant non-compliance was detected, and there are no relevant Low-severity findings</td>
      <td>None</td>
      <td>None</td>
      <td>None</td>
      <td>At least one</td>
      <td>None</td>
    </tr>
    <tr>
      <td>Pass (with findings)</td>
      <td>Every requirement considered relevant for the artifact has at least one test check measuring the participant's compliance with the requirement, and no relevant non-compliance was detected, but there are important findings regarding one or more relevant requirements</td>
      <td>None</td>
      <td>None</td>
      <td>At least one</td>
      <td>Any number</td>
      <td>None</td>
    </tr>
    <tr>
      <td>Not fully verified</td>
      <td>The participant was not detected to be non-compliant with any requirement, but tests could not be successfully conducted to verify compliance to all relevant requirements</td>
      <td>None</td>
      <td>Any number</td>
      <td>Any number</td>
      <td>Any number</td>
      <td>At least one</td>
    </tr>
  </tbody>
</table>

## Troubleshooting "Fail" for a set of tested requirements

If the "Requirement verification status" for a participant is "Fail" (see above for how this is determined), begin troubleshooting by locating the requirement row in the "Tested requirements" table.  Identify the exact checks failed and see if the names alone reveal the issue.  If not, click on the check name to navigate to the documentation for that check and see if the reason for failure can be determined from that documentation.  If not, note the name of the test scenario in which the failed check appears, then find that test scenario run in the [sequence view artifact](../sequence_view) and follow [the instructions to troubleshoot a failed check from the sequence view artifact](../sequence_view/README.md#troubleshooting-a-failed-check).

## Troubleshooting "Not fully verified" for a set of tested requirements

If the "Requirement verification status" for a participant is "Not fully verified" (see above for how this is determined), begin troubleshooting by locating the requirement row for a requirement that was not fully tested in the "Tested requirements" table.  The Requirement cell will be gray rather than green for such requirements.

If that row does not contain any Scenario entries, the test configuration is not capable of verifying compliance to the requirement for any participant and the test designer should be consulted.  The test designer may need to request or contribute a new uss_qualifier feature to verify compliance to the requirement.

If the requirement row contains one or more Scenario entries, these are the test scenarios that are potentially capable of verifying compliance to the requirement.  But, for some reason, the participant's compliance to the requirement was not verified by any of these test scenarios.  For each test scenario capable of verifying compliance to the requirement, review the documentation (linked via the test scenario name) to determine if verification is expected for the participant (for instance, verification may not be expected if verification requires implementing a particular feature and the participant has chosen not to implement that feature).  If verification is expected, consult the index page of the [sequence view artifact](../sequence_view) and find all runs of the test scenario in question.  For each run of the test scenario in question, review the test scenario run page of the sequence view artifact (linked from the test scenario name on the index page).  If the participant does not appear in any of the roles of any of the test scenario runs, the problem may be that the test designer has not included the participant in the relevant environmental resource (e.g., participant has not been added to the list of USSs implementing feature X).  If the participant is involved in one or more runs of the test scenario, trace the events performed to determine why the check that should have verified requirement compliance was not performed for the participant (based on test scenario documentation) -- this is usually because the participant was found to not support an optional capability needed to verify compliance to the requirement.

After performing the above procedure, if the reason for non-verification still cannot be determined, file [a test scenario bug Issue](https://github.com/interuss/monitoring/issues/new?template=bug_test_scenario.md) with InterUSS.  Be sure to attach the entire sequence view artifact and tested requirements artifact when possible, ideally the full zip of artifacts produced from the test run.

## Purple cells

If a test designer explicitly indicates one or more checks in `acceptable_findings`, then failure of this type of check should not affect the status indicated for associated requirements and the test overall.  When the outcome of such a check is ignored in this way, that behavior will be annotated visually with a purple background.  That is, instead of a red background for the failed check, it will be shown with a purple background to indicate that finding has been considered acceptable according to explicit test designer instructions.
