"""Optional comparison arms: run the whole matrix under several configs and
overlay them on the plots. Default is a single arm (no comparison)."""

import dataclasses
from dataclasses import dataclass, field

from monitoring.dss_bench.config import GlobalConfig


@dataclass
class Arm:
    label: str
    overrides: dict = field(default_factory=dict)

    def apply(self, cfg: GlobalConfig) -> GlobalConfig:
        return dataclasses.replace(cfg, **self.overrides)


def single(cfg: GlobalConfig) -> list[Arm]:
    return [Arm(label="baseline")]


def compare_images(img_a: str, img_b: str) -> list[Arm]:
    return [
        Arm(label=img_a, overrides={"dss_image": img_a}),
        Arm(label=img_b, overrides={"dss_image": img_b}),
    ]


def compare_datastores(db_a: str, db_b: str) -> list[Arm]:
    return [
        Arm(label=db_a, overrides={"db_type": db_a}),
        Arm(label=db_b, overrides={"db_type": db_b}),
    ]
