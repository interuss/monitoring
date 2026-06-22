# dss_bench

Benchmark DSS performance as a function of deployment parameters.

For every **context** variant x **test**, it: cleans the local ecosystem,
`make start-locally` with the right env, runs the test against all deployed
DSS at once, and records q/s + latency percentiles. Output is one plot per
test, q/s and latency vs context.

## Layout

- `config.py` - global settings (node count, image, datastore type, duration, processes).
- `environment.py` - wraps `make start-locally` / `down-locally`, resolves DSS targets.
- `auth.py` - mints Dummy OAuth tokens (audience = DSS hostname).
- `driver.py` - runs `processes` processes per DSS for `duration`, times each call.
- `measure.py` - aggregates into total q/s + median/p95 latency.
- `plot.py` - one PNG per test (q/s + latency, one line per comparison arm).
- `arms.py` - optional comparison arms (image vs image, or datastore vs datastore).
- `run.py` - CLI matrix runner.
- `contexts/` - one file per context.
  from 0 to 100 ms).
- `tests/` - one file per test.

## Run

```bash
make image            # build the DSS/monitoring images once
uv run python -m monitoring.dss_bench.run --processes 8 --duration 30
```

## Compare (optional)

Two arms, overlaid on every plot. Omit both flags for no comparison.

```bash
# two PRs / images
uv run python -m monitoring.dss_bench.run --compare-images interuss/dss:pr-A interuss/dss:pr-B
# two datastores
uv run python -m monitoring.dss_bench.run --compare-dbs crdb raft
```

The bench runs on the host: DSS nodes are reached at `http://localhost:80NN`
and tokens carry the matching `dss<j>.uss<i>.localutm` audience, so no extra
container or network is needed.

## Add a context or test

Drop a new file in `contexts/` (subclass `Context`) or `tests/` (subclass `BenchTest`).
