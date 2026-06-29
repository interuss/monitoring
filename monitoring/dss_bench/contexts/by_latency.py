"""Sweep inter-USS network latency from 0 to 100 ms in 10 ms steps.
Jitter is 5% of the base delay; distribution/loss keep the deployment default.
"""

import re

from monitoring.dss_bench.contexts.base import Context, Variant


class ByLatency(Context):
    name = "inter_latency"

    axis_label = "inter-USS netem delay"

    def __init__(
        self,
        delays: list[str] | None = None,
        jitter_frac: float = 0.05,
        correlation: str = "50%",
        distribution: str = "paretonormal",
        loss: str = "0.25% 15%",
    ):
        self.delays = delays or [
            "0ms",
            "10ms",
            "20ms",
            "30ms",
            "40ms",
            "50ms",
            "60ms",
            "70ms",
            "80ms",
            "90ms",
            "100ms",
        ]
        self.jitter_frac = jitter_frac
        self.correlation = correlation
        self.distribution = distribution
        self.loss = loss

    def _line(self, delay: str) -> str:

        # netem rejects `distribution` when base delay is 0; keep only loss there.
        m = re.match(r"([\d.]+)\s*([a-z]*)", delay)
        value = float(m.group(1)) if m else 0.0

        if not m or value == 0:
            return f"loss {self.loss}"

        jitter = f"{value * self.jitter_frac:g}{m.group(2)}"

        return (
            f"delay {delay} {jitter} {self.correlation} "
            f"distribution {self.distribution} loss {self.loss}"
        )

    def variants(self) -> list[Variant]:
        return [
            Variant(label=d, env={"INTER_USS_NETEM_CONF": self._line(d)})
            for d in self.delays
        ]
