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

### Summaries

Each requirement is summarized (see [`TestedRequirement.classname`](./data_types.py)) for a participant in the following way:

* If any test check relevant to that requirement failed, then the compliance
  summary for that requirement is indicated as "Fail".
* Otherwise, if at least one test check measured compliance with the
  requirement did not detect non-compliance, then the compliance summary for
  that requirement is indicated as "Pass".
    * If the summary would be "Pass" but there are one or more low-severity findings (not indicating non-compliance to a requirement), the summary for that requirement is instead indicated as "Pass with findings".
* If no test checks measuring compliance with the requirement were performed
  for the participant, then the compliance summary for that requirement is
  indicated as "Not tested"

The overall "Requirement verification status" for the participant is
summarized in the following way (see [`compute_overall_status`](./summaries.py)):

* If any relevant requirement for the participant indicates "Fail", then the
  overall status is indicated as "Fail".
* Otherwise, if any relevant requirement for the participant indicates "Not
  tested", then the overall status is indicated as "Not fully verified".
* If at least one relevant requirement for the participant indicates "Pass with findings" and all relevant requirements for the participant indicate either "Pass" or "Pass with findings", then the overall status is indicated as "Pass (with findings)".
* If all relevant requirements for the participant indicate "Pass", then the
  overall status is indicated as "Pass".

## Troubleshooting "Fail" for a set of tested requirements

If the "Requirement verification status" for a participant is "Fail" (see above for how this is determined), begin troubleshooting by locating the requirement row in the "Tested requirements" table.  Identify the exact checks failed and see if the names alone reveal the issue.  If not, click on the check name to navigate to the documentation for that check and see if the reason for failure can be determined from that documentation.  If not, note the name of the test scenario in which the first failed check appears, then find that test scenario run in the [sequence view artifact](../sequence_view) and follow [the instructions to troubleshoot a failed check from the sequence view artifact](../sequence_view/README.md#troubleshooting-a-failed-check).

## Troubleshooting "Not fully verified" for a set of tested requirements

If the "Requirement verification status" for a participant is "Not fully verified" (see above for how this is determined), begin troubleshooting by locating the requirement row for a requirement that was not fully tested in the "Tested requirements" table.  The Requirement cell will be gray rather than green for such requirements.

If that row does not contain any Scenario entries, the test configuration is not capable of verifying compliance to the requirement for any participant and the test designer should be consulted.  The test designer may need to request or contribute a new uss_qualifier feature to verify compliance to the requirement.

If the requirement row contains one or more Scenario entries, these are the test scenarios that are potentially capable of verifying compliance to the requirement.  But, for some reason, the participant's compliance to the requirement was not verified by any of these test scenarios.  For each test scenario capable of verifying compliance to the requirement, review the documentation (linked via the test scenario name) to determine if verification is expected for the participant (for instance, verification may not be expected if verification requires implementing a particular feature and the participant has chosen not to implement that feature).  If verification is expected, consult the index page of the [sequence view artifact](../sequence_view) and find all runs of the test scenario in question.  For each run of the test scenario in question, review the test scenario run page of the sequence view artifact (linked from the test scenario name on the index page).  If the participant does not appear in any of the roles of any of the test scenario runs, the problem may be that the test designer has not included the participant in the relevant environmental resource (e.g., participant has not been added to the list of USSs implementing feature X).  If the participant is involved in one or more runs of the test scenario, trace the events performed to determine why the check that should have verified requirement compliance was not performed for the participant (based on test scenario documentation) -- this is usually because the participant was found to not support an optional capability needed to verify compliance to the requirement.

After performing the above procedure, if the reason for non-verification still cannot be determined, file [a test scenario bug Issue](https://github.com/interuss/monitoring/issues/new?template=bug_test_scenario.md) with InterUSS.  Be sure to attach the entire sequence view artifact and tested requirements artifact when possible, ideally the full zip of artifacts produced from the test run.
