from monitoring.local_dss_bench import utils
from monitoring.local_dss_bench.tests.base import BenchTest


def discover() -> dict[str, type[BenchTest]]:
    return {bt.name: bt for bt in utils.discover(__name__, list(__path__), BenchTest)}
