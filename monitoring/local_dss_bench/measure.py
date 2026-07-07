"""Turn raw driver output into q/s and latency percentiles."""

from dataclasses import dataclass


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


@dataclass
class Datapoint:
    label: str
    rps_total: float
    p50_ms: float
    p95_ms: float
    errors: int
    err_p50_ms: float
    err_p95_ms: float
    p50_all_ms: float
    p95_all_ms: float
    rps_per_target: dict[str, float]


def summarize(label: str, results: dict[str, dict], duration_s: float) -> Datapoint:
    """Aggregate the pooled samples into total q/s plus median/p95 latency,
    and keep per-target q/s."""
    merged: list[float] = []
    merged_errors: list[float] = []
    per_target = {}
    for url, d in results.items():
        lat = d["latencies"]
        merged.extend(lat)
        merged_errors.extend(d["error_latencies"])
        per_target[url] = round(len(lat) / duration_s, 2)

    # Distribution including failed calls: a request that ran ~10s then timed
    # out is a 10s+ latency, so folding error timings back in removes the
    # survivorship bias of percentiles computed over successes only.
    with_errors = merged + merged_errors

    return Datapoint(
        label=label,
        rps_total=round(len(merged) / duration_s, 2),
        p50_ms=round(_percentile(merged, 50), 2),
        p95_ms=round(_percentile(merged, 95), 2),
        errors=len(merged_errors),
        err_p50_ms=round(_percentile(merged_errors, 50), 2),
        err_p95_ms=round(_percentile(merged_errors, 95), 2),
        p50_all_ms=round(_percentile(with_errors, 50), 2),
        p95_all_ms=round(_percentile(with_errors, 95), 2),
        rps_per_target=per_target,
    )
