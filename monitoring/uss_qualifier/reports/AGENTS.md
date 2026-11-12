This folder contains definitions for artifacts generated from the output of a uss_qualifier test report.

If your user has requested interpretation, troubleshooting, diagnosis, or similar for a uss_qualifier test report, the instructions below are intended to help with that task.

### Background and objective

uss_qualifier is an automated testing tool developed by InterUSS in this repository (`monitoring`) for the purpose of qualifying systems designed to conduct UTM (UAS traffic management) activities.  A uss_qualifier test run produces a set of artifacts generally containing a subset of the report types defined here.  You will be using these artifacts to determine why a particular outcome occurred, such as a participant being marked as failing or "Not fully verified" for a set of tested requirements.  Your investigation should seek to identify the root causes as deeply as possible with the available information.  A detailed analysis of every failed check is generally undesirable; instead, you should seek to identify the patterns behind multiple check failures and the likely cause(s) of those patterns.  Ideally, your analysis should conclude with one or more top-level suggestions for what participant(s) should change to obtain a fully-passing test result in the future.

### Investigation procedure

Your user should have provided you with a zip file of artifacts, or pointed you to a folder containing artifacts, or provided report.json; if this is not the case, indicate to the user that you require these artifacts to perform the requested task according to these instructions and stop your task unless requested otherwise.  The primary artifact is report.json which is a `TestRunReport` as defined in report.py of this folder.  Note that the version of uss_qualifier that conducted the test run may be different from the codebase version containing these instructions.  The report should, however, still indicate which codebase version was used in report.codebase_version.  If your user has provided a `monitoring` folder with a clone of the InterUSS `monitoring` repository in your workspace, prepare for this investigation by checking out the specified version of uss_qualifier with that repository or asking your user to do this (but take care not to lose any work your user may have been performing in that repository).  If you have a local clone of the `monitoring` repository checked out to the appropriate version, find files and other resources linked from this document in that clone rather than relative to the HTTP location you may have retrieved this document from.

In most investigations, the tested requirements artifact is generally the first artifact to inspect.  status.json provides a machine-readable top-level summary of the status of each participant with regard to the requirements intended to be verified by the test configuration.  Failed or not-fully-verified statuses are usually observations to investigate further.  To troubleshoot these observations, refer to the instructions in [the tested_requirements troubleshooting documentation](./tested_requirements/README.md).  When following these instructions, remember that test scenario documentation may be found in the `monitoring` folder in your workspace if available rather than needing to make HTTP requests.  Following those tested_requirements troubleshooting instructions (including moving to inspection of portions of the sequence view artifact) should allow you to form a holistic understanding of the intent and expectations of each test and what differed in the test run under investigation versus nominal outcomes.

### Responses

In your response, refer users to key specific observations that lead to your conclusions (or example specific observations that illustrate your conclusions) when possible.  When these observations are events that happened during the test run, reference the description of these events in the sequence view artifact.  The shorthand name for a specific event is "sNeM" (for instance, s14e257) referring to the Nth scenario's Mth event, and the sequence view scenario pages contain linkable anchors to each event.

### Special considerations

#### DSS behavior

If troubleshooting involves the behavior of DSS (discovery and synchronization service) instances and your user has provided a `dss` folder with a clone of the InterUSS `dss` repository, this may also be a valuable resource for understanding observed behavior.  Certain portions of the test artifacts may provide information about which version(s) of the DSS were deployed by DSS instance providers, or you may consider asking your user if they know which DSS versions were deployed if this is likely to be important information that you cannot otherwise determine.  DSS behavior can be inspected in the `dss` repository after it is checked out to the appropriate version.

#### Execution errors

A common problem in failed uss_qualifier test runs is an execution error in uss_qualifier.  As noted in [the sequence view documentation](./sequence_view/README.md), execution errors always indicate a uss_qualifier bug and this should be surfaced to your user.  If possible, you should attempt to determine whether this bug has been previously reported and/or fixed by checking [GitHub Issues for the `monitoring` repo](https://github.com/interuss/monitoring/issues).  If the bug has already been reported, your response should mention and/or link to the existing Issue.  If the bug has already been fixed in an existing release, you should note that this problem can be resolved by updating to the more recent codebase version.  If this bug has not yet been reported, please consider offering to draft a bug report using [the appropriate template](https://github.com/interuss/monitoring/issues/new?template=bug_test_scenario.md) and following the [public bug report guidance below](#public-bug-reports) unless the user has specifically requested brevity or similar.  InterUSS finds these bug reports very useful and submitting them for previously-unidentified bugs helps the entire community.

In addition to the above, however, also note to yourself that the majority of execution errors are surfaced because an unusual/untested uss_qualifier code path has been taken because one or more participants have failed in ways not yet exercised by InterUSS.  For instance, many check-failure error message strings are never generated in InterUSS CI tests because there are so many different ways for systems under test to fail.  So, if you are investigating a test run that includes an execution error, an important part of your investigation should be to determine why that bug was elicited in this test run and, presumably, not in more nominal test runs.  The answer to this question is frequently that one or more participants have one or more underlying failures.  In this case, those underlying failures should be emphasized as the most interesting root causes since fixing the InterUSS bug would merely reveal these underlying failures more clearly and cleanly.

### Public bug reports

Test reports may contain sensitive data, and participants may not want to be identified in a public GitHub Issue.  The detailed references useful in your analysis for the user should not automatically be copied into an Issue.  Apply the following guidance when drafting or posting a bug report, including when an Issue template requests test artifacts.

#### Describe the problem with minimal identifying information

When the problem is clear without specifics from the test report, write a self-contained description without referring to that report.  Omit test run IDs, participant names, report-specific scenario/event indices, and other identifying details.  Retain useful technical information such as the affected uss_qualifier version, scenario type or check name, relevant code, error type, and expected versus actual behavior.  Prefer a minimal synthetic reproduction when it conveys the problem adequately; no test artifact attachment is needed in that case.

If explaining the problem requires interactions between actors, use consistent anonymous labels or roles, such as "Participant 1" and "Participant 2" or "tested USS" and "control USS".  For example: "After Participant 2 rejected a modification requested by Participant 1, Participant 1 queried the original operational intent's details and received [...]."  Preserve the sequence and relationships needed to explain the bug without naming the participants.  Use the same labels as any accompanying obfuscated artifacts where possible.

#### Include only the evidence needed to explain the problem

If artifacts would substantially improve developers' ability to understand the problem, select the smallest useful set:

* For a problem wholly contained in one scenario, its sequence view page will usually suffice.
* For the same problem repeated across scenarios, include one representative scenario page, preferably the earliest occurrence, unless additional examples explain a materially different aspect of the bug.
* For a problem caused by interactions across scenarios, include all pages and other files needed to show the cause and its later effects.  Include the sequence view index only if it helps explain those relationships; do not attach the full report by default.

Links to omitted files may remain broken when readers do not need them to follow the Issue description.  For example, an index and two specifically referenced scenario pages may be sufficient even though the index links to many other, omitted pages.  Ensure that references readers do need resolve within the attachment, or provide the necessary context directly in the description.

#### Obfuscate and deliver attachments

Before using or suggesting any test artifacts as Issue attachments, follow [the artifact obfuscation instructions](./obfuscate.md) and run the obfuscation tool on a separate output copy.  Keep the original artifacts unchanged.  Obfuscate related files together so participant and hostname replacements remain consistent, then package only the files selected above.  Do not offer original artifacts as attachments or merely tell the user to obfuscate them later.  If the tool cannot be run, explain the limitation and keep the draft self-contained until obfuscated attachments can be prepared.

Review the resulting files, filenames, and Issue text for remaining sensitive information, including identifying data in free-text errors, URLs, and metadata.  The tool uses heuristics and does not guarantee complete anonymization.  Remove or generalize remaining identifying details while preserving the evidence needed to understand the bug.  When artifact references are necessary, use the obfuscated files' names and event anchors rather than identifiers from the original test report.

Zip the selected obfuscated files if multiple files are relevant or if GitHub does not accept the individual file type as an upload.  Preserve the relative paths needed for navigation within the archive.  Present any prepared attachment to the user with a usable file link, or upload it to the Issue when posting directly within the user's authorized scope.  Do not leave the user with an inaccessible local path or claim an attachment is included without delivering it.
