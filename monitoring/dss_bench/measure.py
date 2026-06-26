"""Turn raw driver output into q/s and latency percentiles."""


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def summarize(results: dict[str, dict], duration_s: float) -> dict:
    """Aggregate across all DSS: total q/s, plus median/p95 latency over the
    pooled samples. Also keeps per-DSS q/s."""
    merged: list[float] = []
    merged_errors: list[float] = []
    per_dss = {}
    for url, d in results.items():
        lat = d["latencies"]
        merged.extend(lat)
        merged_errors.extend(d["error_latencies"])
        per_dss[url] = round(len(lat) / duration_s, 2)

    # Distribution including failed calls: a request that ran ~10s then timed
    # out is a 10s+ latency, so folding error timings back in removes the
    # survivorship bias of percentiles computed over successes only.
    with_errors = merged + merged_errors

    return {
        "rps_total": round(len(merged) / duration_s, 2),
        "p50_ms": round(_percentile(merged, 50), 2),
        "p95_ms": round(_percentile(merged, 95), 2),
        "errors": len(merged_errors),
        "err_p50_ms": round(_percentile(merged_errors, 50), 2),
        "err_p95_ms": round(_percentile(merged_errors, 95), 2),
        "p50_all_ms": round(_percentile(with_errors, 50), 2),
        "p95_all_ms": round(_percentile(with_errors, 95), 2),
        "rps_per_dss": per_dss,
    }
