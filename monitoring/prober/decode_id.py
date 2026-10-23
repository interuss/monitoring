import argparse
import importlib
import pkgutil
import sys

import monitoring.prober
import monitoring.uss_qualifier.scenarios
from monitoring.prober import infrastructure


# Import all tests
def import_submodules(package, recursive=True):
    """Import all submodules of a module, recursively, including subpackages

    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + "." + name
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(description="Decode a test ID")
    parser.add_argument(
        action="store", dest="id", type=str, metavar="ID", help="The ID to decode"
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    import_submodules(monitoring.prober)
    import_submodules(monitoring.uss_qualifier.scenarios)
    decoded = infrastructure.IDFactory.decode_details(args.id)
    id_code = decoded.resource_type
    print(f"Owner: {decoded.owner_name}")
    print(f"Instance index: {decoded.instance_index}")
    if id_code in infrastructure.resource_type_code_descriptions:
        print(
            f"Resource type: {infrastructure.resource_type_code_descriptions[id_code]}"
        )
    else:
        print(f"Resource type: Unregistered ({id_code})")
