# benchmarker

`benchmarker` is a tool for evaluating the performance, throughput, and stability of UTM systems under load.

## Running benchmarker

To execute `benchmarker`, run the following command from the root of the `monitoring` repo:

```bash
PYTHONPATH=. uv run python monitoring/benchmarker/benchmark.py --config file://monitoring/benchmarker/configurations/interuss/isas_uncontended.jsonnet
```

## Security

Warning: benchmarker has the capability of running shell commands specified in the configuration (see `actions`).  Treat the configuration as code and review at an appropriate level of scrutiny before executing.
