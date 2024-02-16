# Sequence view artifact

A sequence view artifact is intended to show a chronological view of what
happened during a test run.  It is mostly useful to developers trying to
understand the context of a test failure or examine the sequence of events
for a test run.

The generated index file contains a list of scenarios and what caused them
to be run (e.g., test suite, action generator, etc).  Each scenario's page
details the events (queries, checks, notes) that occurred during the
execution of that scenario.
