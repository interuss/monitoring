from monitoring.local_dss_bench import utils
from monitoring.local_dss_bench.sweeps.base import Sweep


def discover() -> dict[str, type[Sweep]]:
    return {ct.name: ct for ct in utils.discover(__name__, list(__path__), Sweep)}
