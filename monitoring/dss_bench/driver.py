"""Run a BenchTest with `cfg.processes` processes PER DSS, in parallel across
all DSS, for `cfg.duration_s`. Each process is one sequential caller; q/s
emerges from the number of processes."""

import time
from multiprocessing import Process, Queue

import requests

from monitoring.dss_bench.auth import issue_token
from monitoring.dss_bench.config import GlobalConfig
from monitoring.dss_bench.tests.base import BenchTest


def _worker(
    test: BenchTest,
    target: tuple[str, str],
    cfg: GlobalConfig,
    q: Queue,
) -> None:
    base_url, audience = target
    token = issue_token(cfg.oauth_token_endpoint, cfg.oauth_sub, audience, test.scopes)
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"

    try:
        test.setup(session, base_url)
    except Exception:
        pass

    latencies_ms: list[float] = []
    error_latencies_ms: list[float] = []
    done = 0
    end = time.monotonic() + cfg.duration_s
    while time.monotonic() < end:
        t0 = time.monotonic()
        try:
            test.action(session, base_url)
            latencies_ms.append((time.monotonic() - t0) * 1000.0)
            done += 1
        except Exception:
            # Keep how long the failed call took (e.g. a ~10s timeout) instead
            # of dropping it: discarding slow failures biases percentiles down.
            error_latencies_ms.append((time.monotonic() - t0) * 1000.0)

    try:
        test.teardown(session, base_url)
    except Exception:
        pass

    q.put((base_url, latencies_ms, error_latencies_ms))


def run_test(
    test: BenchTest, targets: list[tuple[str, str]], cfg: GlobalConfig
) -> dict[str, dict]:
    """Return {base_url: {"latencies": [...ms], "error_latencies": [...ms]}}."""
    q: Queue = Queue()
    procs = []
    for target in targets:
        for _ in range(cfg.processes):
            p = Process(target=_worker, args=(test, target, cfg, q))
            p.start()
            procs.append(p)

    results: dict[str, dict] = {
        url: {"latencies": [], "error_latencies": []} for url, _ in targets
    }
    for _ in procs:
        url, lat, err_lat = q.get()
        results[url]["latencies"].extend(lat)
        results[url]["error_latencies"].extend(err_lat)
    for p in procs:
        p.join()

    return results
