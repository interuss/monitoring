# Tracer Log Export Utilities

## ASTM F3548-21 USSLogSet generation

The [`make_usslogset.py`](./make_usslogset.py) script parses a folder of tracer
log files (such as those unzipped from `/tracer/logs.zip`) and exports all
ASTM F3548-21 interactions into a `USSLogSet` JSON file.

### Local invocation via `uv`

From the root of the `monitoring` repository:

```shell
PYTHONPATH=. uv run python monitoring/mock_uss/tracer/export/make_usslogset.py \
  --log-folder /path/to/log/files \
  --output /path/to/usslogset.json
```

### Invocation via Docker

Set `LOG_PATH` to the folder containing the unzipped log files:

```shell
export LOG_PATH=/path/to/log/files
```

Then run the tool, writing to `usslogset.json` in the log file folder:

```shell
docker container run \
  -u "$(id -u):$(id -g)" \
  -v "$LOG_PATH:/logs" \
  interuss/monitoring \
  uv run /app/monitoring/mock_uss/tracer/export/make_usslogset.py \
      --log-folder /logs \
      --output /logs/usslogset.json
```
