# local_dss_bench

Benchmark performance of a local DSS deployment as a function of deployment parameters.

For every **context** in every sweep for each **test**, it: cleans the local ecosystem,
`make start-locally` with the right env, runs the test against the DSS load balancer, and records q/s + latency percentiles. Output is one plot per
test, q/s and latency vs context.

## Layout

- `config.py` - global settings (node count, image, datastore type, duration, processes).
- `environment.py` - wraps `make start-locally` / `down-locally`.
- `driver.py` - runs `processes` processes against the DSS load balancer for `duration`, times each call.
- `measure.py` - aggregates into total q/s + median/p95 latency.
- `plot.py` - one PNG per test (q/s + latency, one line per comparison arm).
- `arms.py` - optional comparison arms (image vs image, or datastore vs datastore).
- `run.py` - CLI matrix runner.
- `sweeps/` - one file per sweep.
  from 0 to 100 ms).
- `tests/` - one file per test.

## Run

```bash
uv run python -m monitoring.local_dss_bench.run --processes 8 --duration 30
```

## Compare (optional)

Two arms, overlaid on every plot. Omit both flags for no comparison.

```bash
# two PRs / images
uv run python -m monitoring.local_dss_bench.run --compare-images interuss/dss:pr-A interuss/dss:pr-B
# two datastores
uv run python -m monitoring.local_dss_bench.run --compare-datastores crdb raft
```

The bench runs on the host and reaches the DSS load balancer at
`http://localhost:8090`.

## Add a sweep or test

Drop a new file in `sweeps/` (subclass `Sweep`) or `tests/` (subclass `BenchTest`).
