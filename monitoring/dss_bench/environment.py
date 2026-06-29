"""Drive `make start-locally` / `make down-locally` and resolve DSS targets.

Each DSS node is published on the host at port 80<NN> where NN is the
2-digit global node index, and validates JWTs whose audience equals its
hostname dss<j>.uss<i>.localutm. We therefore hit http://localhost:80NN
while minting tokens for that audience.
"""

import os
import subprocess
from pathlib import Path

from monitoring.dss_bench.config import GlobalConfig

REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(cfg: GlobalConfig, extra: dict[str, str]) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "NUM_USS": str(cfg.num_uss),
            "NUM_NODES": str(cfg.num_nodes),
            "DSS_IMAGE": cfg.dss_image,
            "DB_TYPE": cfg.db_type,
            "INTRA_USS_NETEM_CONF": cfg.intra_netem,
            "INTER_USS_NETEM_CONF": cfg.inter_netem,
        }
    )
    env.update(extra)
    return env


def up(cfg: GlobalConfig, extra: dict[str, str]) -> None:
    subprocess.run(
        ["make", "start-locally"], cwd=REPO_ROOT, env=_env(cfg, extra), check=True
    )


def down(cfg: GlobalConfig) -> None:
    subprocess.run(
        ["make", "clean-locally"], cwd=REPO_ROOT, env=_env(cfg, {}), check=False
    )


def dss_targets(cfg: GlobalConfig) -> list[tuple[str, str]]:
    """Return (base_url, jwt_audience) for every deployed DSS node."""
    targets = []
    for i in range(1, cfg.num_uss + 1):
        for j in range(1, cfg.num_nodes + 1):
            node_idx = (i - 1) * cfg.num_nodes + j
            url = f"http://localhost:80{node_idx:02d}"
            audience = f"dss{j}.uss{i}.localutm"
            targets.append((url, audience))
    return targets
