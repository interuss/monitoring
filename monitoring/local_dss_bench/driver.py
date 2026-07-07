"""Run a BenchTest with `cfg.processes` processes hitting the DSS load
balancer in parallel for `cfg.duration_s`. Each process is one sequential
caller; q/s emerges from the number of processes."""

import time
from multiprocessing import Process, Queue

from monitoring.local_dss_bench.config import GlobalConfig
from monitoring.local_dss_bench.tests.base import BenchTest
from monitoring.monitorlib.auth import DummyOAuth
from monitoring.monitorlib.infrastructure import UTMClientSession


def _worker(
    test: BenchTest,
    base_url: str,
    cfg: GlobalConfig,
    q: Queue,
) -> None:
    session = UTMClientSession(
        base_url, DummyOAuth(cfg.oauth_token_endpoint, cfg.oauth_sub)
    )
    session.default_scopes = test.scopes

    try:
        test.setup(session, base_url)
    except Exception:
        q.put((base_url, [], []))
        return

    latencies_ms: list[float] = []
    error_latencies_ms: list[float] = []
    end = time.monotonic() + cfg.duration_s
    while time.monotonic() < end:
        t0 = time.monotonic()
        try:
            test.action(session, base_url)
            latencies_ms.append((time.monotonic() - t0) * 1000.0)
        except Exception:
            # Keep how long the failed call took (e.g. a ~10s timeout) instead
            # of dropping it: discarding slow failures biases percentiles down.
            error_latencies_ms.append((time.monotonic() - t0) * 1000.0)

    try:
        test.teardown(session, base_url)
    except Exception:
        pass

    q.put((base_url, latencies_ms, error_latencies_ms))


LB_URL = "http://localhost:8090"


def run_test(test: BenchTest, cfg: GlobalConfig) -> dict[str, dict]:
    """Return {base_url: {"latencies": [...ms], "error_latencies": [...ms]}}."""
    q: Queue = Queue()
    procs = []
    for _ in range(cfg.processes):
        p = Process(target=_worker, args=(test, LB_URL, cfg, q))
        p.start()
        procs.append(p)

    results: dict[str, dict] = {LB_URL: {"latencies": [], "error_latencies": []}}
    for _ in procs:
        url, lat, err_lat = q.get()
        results[url]["latencies"].extend(lat)
        results[url]["error_latencies"].extend(err_lat)
    for p in procs:
        p.join()

    return results
