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

Each requirement is summarized for a participant in the following way:

* If any test check relevant to that requirement failed, then the compliance
  summary for that requirement is indicated as "Fail".
* Otherwise, if at least one test check measured compliance with the
  requirement did not detect non-compliance, then the compliance summary for
  that requirement is indicated as "Pass".
* If no test checks measuring compliance with the requirement were performed
  for the participant, then the compliance summary for that requirement is
  indicated as "Not tested"

The overall "Requirement verification status" for the participant is
summarized in the following way:

* If any relevant requirement for the participant indicates "Fail", then the
  overall status is indicated as "Fail".
* Otherwise, if any relevant requirement for the participant indicates "Not
  tested", then the overall status is indicated as "Not fully verified".
* If all relevant requirements for the participant indicate "Pass", then the
  overall status is indicated as "Pass".
