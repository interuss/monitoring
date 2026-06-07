# DSS Performance Log Acquisition

This utility acquires, normalizes, and combines HTTP server performance logs from Zap-based DSS servers into a standardized JSON format. The output is structured to group logs by their container/server origin and is sorted chronologically.

The normalized JSON format is:
```json
{
  "origins": {
    "server-origin-1": [
      {
        "timestamp": "2026-06-07T17:38:15.120Z",
        "method": "GET",
        "path": "/v1/dss/operational_intent_references/1234",
        "proto": "HTTP/1.1",
        "status_code": 200,
        "duration_ms": 3.0,
        "peer_address": "127.0.0.1:12345",
        "req_sub": "client-name"
      }
    ]
  }
}
```

## Running the tool

Run the script using the `uv` project workspace in the `monitoring` directory:

```shell
uv run monitoring/analysis/dss_performance/acquire_logs.py [ARGS]
```

### Command-line Arguments

- `--style`: (Required) Either `docker` or `gcloud`.
- `--output`: (Required) The path to the output JSON file. The tool will automatically create directories, load the existing file if present, append new entries, sort them chronologically, and deduplicate identical logs.
- `--origin`:
  - For `docker` style: The fixed name of the container/origin (default: `docker-container`).
  - For `gcloud` style: Optional default origin name or format template string.
- `--origin-format`:
  - For `gcloud` style: A format template string (default: `{pod_name}`) supporting resource labels like `{pod_name}`, `{container_name}`, `{cluster_name}`, or `{namespace_name}`.

---

## Acquisition Examples

### 1. Local Docker Container

To acquire logs from a local container named `local_infra_1-1-dss-1`:

```shell
docker logs local_infra_1-1-dss-1 2>&1 | \
  uv run monitoring/analysis/dss_performance/acquire_logs.py \
    --style docker \
    --origin local_infra_1-1-dss-1 \
    --output monitoring/analysis/dss_performance/acquired_logs.json
```

### 2. Google Cloud Logging (gcloud)

To acquire logs from Google Cloud, you **must** specify `--format="json(jsonPayload, resource.labels)"` in your `gcloud` command. This ensures the output is valid JSON containing both the log payload and the Kubernetes labels required to distinguish container instances.

Here is an example acquiring logs from a cluster named `my-cluster` within a time range, filtering out health checks, and labeling logs by pod name:

```shell
gcloud logging read '
  resource.type="k8s_container"
  resource.labels.cluster_name="my-cluster"
  labels.k8s-pod/app="core-service"
  jsonPayload.msg!="GET /healthy HTTP/1.1"
  timestamp >= "2026-06-07T00:00:00Z"
  timestamp <= "2026-06-07T23:59:59Z"
' \
  --project="your-project-id" \
  --format="json(jsonPayload, resource.labels)" | \
  uv run monitoring/analysis/dss_performance/acquire_logs.py \
    --style gcloud \
    --origin-format "{pod_name}" \
    --output monitoring/analysis/dss_performance/acquired_logs.json
```

To include container name or namespace in the origin key (e.g. `core-service/pod-xyz`), you can customize the `--origin-format` string:

```shell
--origin-format "{container_name}/{pod_name}"
```

---

## Visualizing Latency Performance

Once logs have been acquired in `acquired_logs.json`, you can generate an interactive standalone HTML dashboard to analyze DSS handler latency over time:

```shell
uv run monitoring/analysis/dss_performance/visualize_latency.py [INPUT_JSON] [OUTPUT_HTML]
```

### Arguments

- `INPUT_JSON`: Optional. Path to the input JSON file (default: `acquired_logs.json`).
- `OUTPUT_HTML`: Optional. Path to the output HTML file (default: `latency_visualization.html`).
