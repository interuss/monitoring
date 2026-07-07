"""Drive `make start-locally` / `make down-locally`."""

import os
import subprocess
from pathlib import Path

from monitoring.local_dss_bench.config import GlobalConfig

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
