"""Run the (sweep x test) matrix and emit one plot per test."""

import argparse
import dataclasses
import json
from pathlib import Path

from monitoring.local_dss_bench import arms, environment, measure, plot, sweeps, tests
from monitoring.local_dss_bench.config import GlobalConfig
from monitoring.local_dss_bench.driver import run_test
from monitoring.local_dss_bench.measure import Datapoint
from monitoring.local_dss_bench.sweeps.base import Sweep

# Auto-discovered from the sweeps/ and tests/ packages.
SWEEPS = sweeps.discover()  # name -> Sweep subclass
TESTS = tests.discover()  # name -> BenchTest subclass
DEFAULT_SWEEP = sorted(SWEEPS)[0] if SWEEPS else None
DEFAULT_TESTS = sorted(n for n, cls in TESTS.items() if cls.default)


def parse_args() -> tuple[GlobalConfig, list[arms.Arm], Sweep, list, Path]:

    defaults = GlobalConfig()

    p = argparse.ArgumentParser()
    p.add_argument("--num-uss", type=int, default=defaults.num_uss)
    p.add_argument("--num-nodes", type=int, default=defaults.num_nodes)
    p.add_argument("--dss-image", default=defaults.dss_image)
    p.add_argument("--db-type", default=defaults.db_type)
    p.add_argument(
        "--duration",
        type=float,
        default=defaults.duration_s,
        help="This option requires keeping this value high, especially with a low Q/s, to ensure enough samples are collected.",
    )
    p.add_argument("--processes", type=int, default=defaults.processes)
    p.add_argument("--intra-netem", default=defaults.intra_netem)
    p.add_argument("--inter-netem", default=defaults.inter_netem)
    p.add_argument(
        "--sweep",
        choices=sorted(SWEEPS),
        default=DEFAULT_SWEEP,
        help="Which sweep to apply (only one per run).",
    )
    p.add_argument(
        "--tests",
        nargs="+",
        choices=sorted(TESTS),
        default=DEFAULT_TESTS,
        help=f"Which tests to run (default: {', '.join(DEFAULT_TESTS)}).",
    )
    p.add_argument("--outdir", default="dss_bench_out")

    # Optional comparison (mutually exclusive). Omit both for no comparison.
    cmp = p.add_mutually_exclusive_group()
    cmp.add_argument("--compare-images", nargs=2, metavar=("IMG_A", "IMG_B"))
    cmp.add_argument("--compare-datastores", nargs=2, metavar=("DB_A", "DB_B"))

    a = p.parse_args()

    cfg = GlobalConfig(
        num_uss=a.num_uss,
        num_nodes=a.num_nodes,
        dss_image=a.dss_image,
        db_type=a.db_type,
        duration_s=a.duration,
        processes=a.processes,
        intra_netem=a.intra_netem,
        inter_netem=a.inter_netem,
    )

    if a.compare_images:
        run_arms = arms.compare_images(*a.compare_images)
    elif a.compare_datastores:
        run_arms = arms.compare_datastores(*a.compare_datastores)
    else:
        run_arms = arms.single(cfg)

    sweep = SWEEPS[a.sweep]()
    selected_tests = [TESTS[name]() for name in a.tests]

    return cfg, run_arms, sweep, selected_tests, Path(a.outdir)


def main() -> None:

    cfg, run_arms, sweep, selected_tests, outdir = parse_args()

    # by_test[test][arm_label] = [point per sweep variant]
    by_test: dict[str, dict[str, list[Datapoint]]] = {
        t.name: {} for t in selected_tests
    }

    variants = sweep.variants()
    total = len(run_arms) * len(variants)
    step = 0

    for arm in run_arms:
        arm_cfg = arm.apply(cfg)

        for variant in variants:
            step += 1
            print(
                f"[{step}/{total} {100 * step // total}%] "
                f"[{arm.label}][{sweep.name}] variant={variant.label} "
                f"image={arm_cfg.dss_image} db={arm_cfg.db_type}"
            )

            environment.down(arm_cfg)
            environment.up(arm_cfg, variant.env)
            for test in selected_tests:
                raw = run_test(test, arm_cfg)

                point = measure.summarize(variant.label, raw, arm_cfg.duration_s)
                by_test[test.name].setdefault(arm.label, []).append(point)

                print(
                    f"  {test.name}: {point.rps_total} q/s "
                    f"p50={point.p50_ms}ms p95={point.p95_ms}ms "
                    f"errors={point.errors}"
                )

        environment.down(arm_cfg)

    meta = {
        "sweep": sweep.name,
        "num_uss": cfg.num_uss,
        "num_nodes": cfg.num_nodes,
        "processes": cfg.processes,
        "duration_s": cfg.duration_s,
        "datastore": cfg.db_type,
        "image": cfg.dss_image,
        "intra_netem": cfg.intra_netem,
        "inter_netem": cfg.inter_netem,
    }
    if len(run_arms) > 1:
        meta["arms"] = ", ".join(a.label for a in run_arms)

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "results.json").write_text(
        json.dumps(
            {"meta": meta, "by_test": by_test}, indent=2, default=dataclasses.asdict
        )
    )
    paths = plot.render(by_test, outdir, sweep.variable_label, meta)
    print("Plots:", ", ".join(str(p) for p in paths))


if __name__ == "__main__":
    main()
