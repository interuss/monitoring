# uss_qualifier reports

## Report types

uss_qualifier is capable of generating a range of artifacts from a test run, each intended to fulfill a different purpose.  Part of a [test configuration](../configurations) defines artifacts that should be produced by the test run.

### Raw report

The raw output of the test run is a raw [TestRunReport](./report.py), which can be produced with the `raw_report` artifact option and has the file name `report.json`.  This data structure contains all information about a test run considered relevant, and other artifacts are merely views into a subset of this information.

#### Other artifact generation from raw report

Given a `report.json`, any other artifacts can be generated with [`make_artifacts.sh`](../make_artifacts.sh).  From the repository root, for instance: `monitoring/uss_qualifier/make_artifacts.sh file://output/report.json configurations.personal.my_artifacts`.  That command loads the report at monitoring/uss_qualifier/output/report.json along with the configuration at monitoring/configurations/personal/my_artifacts.yaml and write the artifacts defined in the my_artifacts configuration.

To regenerate artifacts using just a raw TestRunReport (using the configuration embedded in the TestRunReport), only specify the report.  For example: `monitoring/uss_qualifier/make_artifacts.sh file://output/report.json`

### Tested requirements

The [tested requirements artifact](./tested_requirements) summarizes a test run's demonstration of a USS's compliance with a set of requirements.

### Sequence view

The [sequence view artifact](./sequence_view) is a human-readable description/log of what happened during a test run.  This artifact is a good starting point to understand or debug what happened during a test run.
