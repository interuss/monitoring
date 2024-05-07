---
name: Test scenario bug
about: I don't think a particular outcome from uss_qualifier is correct
labels: test-scenario-behavior, automated-testing
---

*Note: remove this note and replace all template instructions below with your content before submitting this issue*

**Observed behavior**
Describe the observed behavior in enough detail for contributors to at least unambiguously understand what is happening, and ideally to reproduce.  Excellent means to accomplish this are:

* A zip file of a sequence view artifact
* A zip file of report.json

Other acceptable means might include:

* A screenshot of the relevant portions of a sequence view artifact (though it can be difficult to determine what is relevant if the problem is not known) plus an indication of codebase version
* A direct reference to the location of the known problem in code, along with a description of what happens due to that problem

Troubleshooting test behavior without report.json or a sequence view zip can be very difficult so most issues of this type should have a report.json or sequence view zip attached.

**Test check**
Identify the test check that unexpectedly succeeded, failed, or wasn't checked -- try to limit a single GitHub issue to a single test check to investigate.  "First failed_check" is fine, or a line number in the attached report.json or scenario index + event index in the attached sequence view is ideal.

**Difference from expected behavior**
Explain why you think there is a problem with the observed behavior.  For instance, "The test scenario seems to assume that all USSs must do X but my USS does Y instead and I think I'm still compliant with all the standard requirements being tested."  Or, "The test report says I didn't do X but I think I actually did do X because of evidence Y."

**Additional context**
Add any other context about the problem here, or remove this section.
