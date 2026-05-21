import argparse
import json
import sys

import yaml
from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.files import ExternalFile, load_dict
from monitoring.uss_qualifier.resources.interuss.geospatial_map import (
    FeatureCheckTableResource,
)
from monitoring.uss_qualifier.resources.interuss.geospatial_map.feature_check_table import (
    FeatureCheckTableSpecification,
)


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(description="Generate a FeatureCheckTable ")
    parser.add_argument(
        "--config-path",
        action="store",
        dest="config_path",
        type=str,
        help="Path to dict-like file containing a FeatureCheckTableSpecification (may have an anchor suffix like #/foo/bar)",
    )
    return parser.parse_args(argv)


def generate_table(path: str):
    spec_dict = load_dict(ExternalFile(path=path))
    spec = ImplicitDict.parse(spec_dict, FeatureCheckTableSpecification)
    resource = FeatureCheckTableResource(specification=spec, resource_origin="Script")
    print(yaml.dump(json.loads(json.dumps(resource.table)), indent=2))


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    generate_table(args.config_path)
