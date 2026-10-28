import argparse
import sys

import monitoring.uss_qualifier.scenarios
from monitoring.monitorlib import ids
from monitoring.monitorlib.inspection import import_submodules


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(description="Decode a test ID")
    parser.add_argument(
        action="store", dest="id", type=str, metavar="ID", help="The ID to decode"
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    import_submodules(monitoring.uss_qualifier.scenarios)
    decoded = ids.IDFactory.decode_details(args.id)
    id_code = decoded.resource_type
    print(f"Owner: {decoded.owner_name}")
    print(f"Instance index: {decoded.instance_index}")
    if id_code in ids.resource_type_code_descriptions:
        print(f"Resource type: {ids.resource_type_code_descriptions[id_code]}")
    else:
        print(f"Resource type: Unregistered ({id_code})")
