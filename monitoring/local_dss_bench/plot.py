"""One plot per test, comparing arms. Top subplot: total q/s vs context.
Bottom subplot: latency vs context (p50 dashed, p95 solid). One color per arm."""

from pathlib import Path

import matplotlib

from monitoring.local_dss_bench.measure import Datapoint

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render(
    by_test: dict[str, dict[str, list[Datapoint]]],
    outdir: Path,
    axis_label: str = "context",
    meta: dict | None = None,
) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    meta_text = "  |  ".join(f"{k}={v}" for k, v in meta.items()) if meta else ""
    paths = []
    for test_name, by_arm in by_test.items():
        fig, (ax_rps, ax_lat, ax_err) = plt.subplots(
            3, 1, figsize=(10, 12), sharex=True
        )
        colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        for idx, (arm_label, points) in enumerate(by_arm.items()):
            labels = [p.label for p in points]
            color = colors[idx % len(colors)]
            ax_rps.plot(
                labels,
                [p.rps_total for p in points],
                marker="s",
                color=color,
                label=arm_label,
            )
            ax_lat.plot(
                labels,
                [p.p95_ms for p in points],
                marker="o",
                color=color,
                label=f"{arm_label} p95",
            )
            ax_lat.plot(
                labels,
                [p.p50_ms for p in points],
                marker="o",
                linestyle="--",
                color=color,
                alpha=0.6,
                label=f"{arm_label} p50",
            )
            ax_lat.plot(
                labels,
                [p.p95_all_ms for p in points],
                marker=".",
                linestyle=":",
                color=color,
                alpha=0.45,
                label=f"{arm_label} p95 (incl. errors)",
            )
            ax_err.plot(
                labels,
                [p.errors for p in points],
                marker="x",
                color=color,
                label=arm_label,
            )

        ax_rps.set_ylabel("q/s (all DSS)")
        ax_rps.legend(loc="best")
        ax_lat.set_ylabel("latency (ms)")
        ax_lat.legend(loc="best")
        ax_err.set_ylabel("errors (count)")
        ax_err.set_xlabel(axis_label)
        ax_err.legend(loc="best")
        fig.suptitle(test_name)
        if meta_text:
            fig.text(
                0.5, 0.005, meta_text, ha="center", va="bottom", fontsize=7, wrap=True
            )
        fig.tight_layout(rect=(0, 0.04, 1, 1))

        path = outdir / f"{test_name}.png"
        fig.savefig(path, dpi=120)
        plt.close(fig)
        paths.append(path)
    return paths
