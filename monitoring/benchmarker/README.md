# benchmarker

`benchmarker` is a tool for evaluating the performance, throughput, and stability of UTM systems under load.

## Background

Most systems roughly follow the Universal Scalability Law<sup>[1](https://www.graphiumlabs.com/blog/part2-gunthers-universal-scalability-law),[2](https://raw.githubusercontent.com/VividCortex/ebooks/master/scalability.pdf)</sup> model that includes three effects:

1. At low load, each additional unit of load is handled with the same efficiency.  So, achieved throughput scales linearly with load.  Achieved throughput is successful operations per time.
2. But, there are likely some shared resources and higher loads increase contention for those shared resources.  This causes throughput to fall away from linear scaling toward an asymptotic maximum throughput.
3. Even worse, maintaining coherence between processing units may require crosstalk which is a cost that scales with load.  The marginal throughput from additional load falls to zero due to effect 2 above (contention), but then this additional coherency penalty means that throughput eventually decreases with increasing load.

Combining the three effects above means that the graph of throughput versus load usually looks qualitatively similar to this:

![Universal Scalability Law curve](./assets/USL.png)

The max throughput point shown above is an extremely important point. The system should never be operated in the operational regime to the right of the max throughput point. Any performance metrics captured in the regime to the right of this max throughput point are invalid as they could be improved almost for free with load shedding.

Even the max throughput point is not one we want to reach because requests at that point will be served with very high latency compared to requests served at lower load/throughput. Instead, this max throughput point should be the absolute maximum load the system should see when working through a burst of load.

Therefore, load tests should be conducted such that metrics are reported from the left side of this curve.  If DSS latency is consistenly above ~6 seconds, it is very likely the load applied is on the right (wrong) side of the curve above.  When DSS latency averages near 10 seconds (the operation-abort timeout threshold), it is almost certain the applied load is on the right (wrong) side of the curve.

Benchmarker generally tries to characterize the left side of this curve, often slightly past the peak throughput point when this point exists (it almost always does).

## Behavior

Benchmarker applies variable loads to a system and measures the resulting achieved throughputs, defined as successful operations per time.  It effectively populates scatter points on the conceptual USL graph above with each scatter point's X position selected by level of load applied (load factor) and Y position determined by measuring achieved throughput at that load.

### Loads

The benchmarker framework can support a wide variety of very different types of loads, but the primary type of load curently is a variable number of virtual users who perform operations on the system under test.

### Users

The only type of virtual user currently is a virtual user who plans and executes flights.  Their behavior is broadly configurable including:

* Planning flights (where flights are located, how long they are, how large they are, how much delay in between flights, etc)
* Executing flights (requiring on-time takeoff, ending early, etc)
* UTM operations (whether to perform F3411 NetRID and/or F3548 SCD, strategies used to perform those roles, etc)

### Operations

The fundamental unit of work measurement in benchmarker is an "operation".  Many operations are queries; for instance createOperationalIntentReference in the DSS.  Query operations begin when a request is dispatched and end when a response is received.  Other operations involve workflows rather than queries; for instance, an operation corresponding with a virtual flight's "active" time begins when the virtual flight becomes active and ends when the virtual flight is completed.  Workflow operations can involve multiple sub-operations.

The most important operation for a flight-planning virtual user is a "flight".  This operation begins with the first action taken to enable the flight (e.g., sharing an F3548 operational intent) and ends with the completion of the last action relating to that flight (e.g., transitioning the F3548 operational intent to ended).  A single flight with UTM support services generally involves multiple queries.  So, one flight operation per second (FPS) implies multiple queries per second (QPS).

## Running benchmarker

### Configuration design

Similar to [uss_qualifier](../uss_qualifier), benchmarker accepts a configuration as input and performs the actions specified by that configuration.  A benchmarker configuration is dict content (JSON, YAML, Jsonnet, etc) that follows the [BenchmarkConfiguration schema](../../schemas/monitoring/benchmarker/configurations/configuration/BenchmarkConfiguration.json) to describe a [BenchmarkConfiguration object](./configurations/configuration.py).  Example configurations can be found in [the interuss configurations folder](./configurations/interuss/).  Performance measurements can vary a great deal depending on measurement specifics and benchmarker is very flexible, so it is important to ensure the configuration used accurately represents the scenarios to be tested.

### Security

Warning: benchmarker has the capability of running shell commands specified in the configuration (see [`actions`](./configurations/actions/)).  Treat benchmarker configurations as code and review at an appropriate level of scrutiny before executing.

### Execution

To execute benchmarker, run a command like the one below from the root of the `monitoring` repo, using the configuration designed as above:

```bash
PYTHONPATH=. uv run python monitoring/benchmarker/benchmark.py --config file://monitoring/benchmarker/configurations/interuss/isas_uncontended.jsonnet
```

### Generating artifacts from a report

If you already have a `BenchmarkRunReport` file generated by a previous run of benchmarker ([`benchmark.py`](./benchmark.py)), you can regenerate its artifacts without re-running the benchmark measurement using [`make_artifacts.py`](./make_artifacts.py):

```bash
PYTHONPATH=. uv run python monitoring/benchmarker/make_artifacts.py --report file://monitoring/benchmarker/output/isas_uncontended/report.json
```

You can also specify `--config` if you wish to generate artifacts using a configuration different from the one embedded in the report:

```bash
PYTHONPATH=. uv run python monitoring/benchmarker/make_artifacts.py --report file://monitoring/benchmarker/output/isas_uncontended/report.json --config file://monitoring/benchmarker/configurations/interuss/isas_uncontended.jsonnet
```

## Architecture

Benchmarker is implemented in the following modules:

* [`configurations`](./configurations/): definitions of inputs to benchmarker
* [`engine`](./engine/): main executable code to read the configuration input, apply load, and measure throughput
* [`reports`](./reports/): definitions of result/output data formats
* [`artifacts`](./artifacts/): generation code to create the output artifacts

Fundamentally, benchmarker is a tool to convert a configuration to a report.  It also generates artifacts, but all artifacts can also/instead be generated after the fact from a full [BenchmarkReport](./reports/report.py).
