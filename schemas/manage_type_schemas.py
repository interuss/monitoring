import argparse
import enum
import inspect
import json
import os
import sys
from typing import Optional, Set, Dict, Type, get_type_hints, get_args, get_origin

import implicitdict
from implicitdict import ImplicitDict
import implicitdict.jsonschema
from implicitdict.jsonschema import SchemaVars, SchemaVarsResolver
from loguru import logger

import monitoring
import monitoring.uss_qualifier.action_generators
import monitoring.uss_qualifier.resources
from monitoring.monitorlib.inspection import fullname, import_submodules
from monitoring.uss_qualifier.action_generators.action_generator import ActionGenerator
from monitoring.uss_qualifier.configurations.configuration import (
    USSQualifierConfiguration,
)
from monitoring.uss_qualifier.reports.report import TestRunReport
from monitoring.uss_qualifier.resources.resource import Resource


class Action(str, enum.Enum):
    Check = "Check"
    Generate = "Generate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage auto-generated JSON Schemas")

    parser.add_argument(
        "--generate",
        dest="action",
        action="store_const",
        const=Action.Generate,
        help="Create, update, and delete JSON Schema files to match code objects",
    )

    parser.add_argument(
        "--check",
        dest="action",
        action="store_const",
        const=Action.Check,
        help="Just check whether JSON Schema files match code objects",
    )

    return parser.parse_args()


def _make_type_schemas(
    parent: Type[ImplicitDict],
    reference_resolver: SchemaVarsResolver,
    repo: Dict[str, dict],
    already_checked: Optional[Set[str]] = None,
) -> None:
    implicitdict.jsonschema.make_json_schema(parent, reference_resolver, repo)
    if already_checked is None:
        already_checked = set()
    already_checked.add(fullname(parent))

    # TODO: Expose get_fields formally in implicitdict
    all_fields, _ = implicitdict._get_fields(parent)
    hints = get_type_hints(parent)
    for field in all_fields:
        if field not in hints:
            continue
        field_type = hints[field]

        pending_types = [field_type]
        while pending_types:
            pending_type = pending_types.pop(0)
            generic_type = get_origin(pending_type)
            if generic_type:
                pending_types.extend(get_args(pending_type))
            else:
                if (
                    issubclass(pending_type, ImplicitDict)
                    and fullname(pending_type) not in already_checked
                ):
                    _make_type_schemas(
                        pending_type, reference_resolver, repo, already_checked
                    )


def _find_specifications(
    module,
    repo: Dict[str, Type[ImplicitDict]],
    already_checked: Optional[Set[str]] = None,
) -> None:
    if already_checked is None:
        already_checked = set()
    already_checked.add(module.__name__)

    for name, member in inspect.getmembers(module):
        if (
            inspect.ismodule(member)
            and member.__name__ not in already_checked
            and member.__name__.startswith("monitoring")
        ):
            _find_specifications(member, repo, already_checked)
        elif inspect.isclass(member):
            if issubclass(member, Resource) and member != Resource:
                spec_type = get_args(member.__orig_bases__[0])[0]
                repo[fullname(spec_type)] = spec_type
            elif issubclass(member, ActionGenerator) and member != ActionGenerator:
                spec_type = get_args(member.__orig_bases__[0])[0]
                repo[fullname(spec_type)] = spec_type


def main() -> int:
    args = parse_args()

    if args.action is None:
        raise ValueError(
            "Invalid usage; action must be specified with --check or --generate flags"
        )

    def schema_vars_resolver(schema_type: Type) -> SchemaVars:
        if schema_type.__module__ in {"builtins", "typing"}:
            return SchemaVars(name=schema_type.__name__)

        def path_of_py_file(t: Type) -> str:
            top_module = t.__module__.split(".")[0]
            module_path = os.path.dirname(sys.modules[top_module].__file__)
            py_file_path = inspect.getfile(t)
            return os.path.join(
                top_module, os.path.relpath(py_file_path, start=module_path)
            )

        def full_name(t: Type) -> str:
            return t.__module__ + "." + t.__qualname__

        def path_of_schema_file(t: Type) -> str:
            return "schemas/" + "/".join(full_name(t).split(".")) + ".json"

        def path_to(t_dest: Type, t_src: Type) -> str:
            path_to_dest = path_of_schema_file(t_dest)
            path_to_src = os.path.dirname(path_of_schema_file(t_src))
            rel_path = os.path.relpath(path_to_dest, start=path_to_src)
            if rel_path[0] != ".":
                rel_path = os.path.join("", rel_path)
            return rel_path

        rel_path = path_of_schema_file(schema_type)

        return SchemaVars(
            name=rel_path,
            path_to=path_to,
            schema_id="https://github.com/interuss/monitoring/blob/main/" + rel_path,
            description=f"{full_name(schema_type)}, as defined in {path_of_py_file(schema_type)}",
        )

    schemas = {}
    _make_type_schemas(TestRunReport, schema_vars_resolver, schemas)
    _make_type_schemas(USSQualifierConfiguration, schema_vars_resolver, schemas)

    repo = {}
    import_submodules(monitoring.uss_qualifier.resources)
    _find_specifications(monitoring.uss_qualifier.resources, repo)
    import_submodules(monitoring.uss_qualifier.action_generators)
    _find_specifications(monitoring.uss_qualifier.action_generators, repo)
    for spec_type in repo.values():
        implicitdict.jsonschema.make_json_schema(
            spec_type, schema_vars_resolver, schemas
        )

    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(monitoring.__file__), "..")
    )

    changes = 0

    # Check for non-current schemas that need to be removed
    for dirpath, _, filenames in os.walk(os.path.join(repo_root, "schemas")):
        for filename in filenames:
            rel_filename = os.path.relpath(
                os.path.join(dirpath, filename), start=repo_root
            )
            if not rel_filename.lower().endswith(".json"):
                continue
            if rel_filename in schemas:
                continue

            if args.action == Action.Check:
                logger.error(
                    f"{rel_filename} does not correspond with a current code object"
                )
                changes += 1
            elif args.action == Action.Generate:
                logger.info(f"Removing {rel_filename}")
                os.remove(os.path.join(dirpath, filename))
                changes += 1
            else:
                raise NotImplementedError(
                    f"Action {args.action} is not yet implemented"
                )

    # Check/update every current schema
    for rel_filename, schema in schemas.items():
        filename = os.path.abspath(os.path.join(repo_root, rel_filename))
        if os.path.exists(filename):
            with open(filename, "r") as f:
                old_value = json.load(f)
            if schema == old_value:
                continue
        changes += 1

        if args.action == Action.Check:
            logger.error(f"{rel_filename} schema does not match current code object")
        elif args.action == Action.Generate:
            dir_name = os.path.dirname(
                os.path.abspath(os.path.join(repo_root, filename))
            )
            os.makedirs(dir_name, exist_ok=True)
            logger.info(f"Updating {rel_filename}")
            with open(filename, "w") as f:
                json.dump(schema, f, indent=2, sort_keys=True)
        else:
            raise NotImplementedError(f"Action {args.action} is not yet implemented")

    # Terminate appropriately depending on action and outcome
    if changes > 0:
        if args.action == Action.Check:
            logger.error(
                f"JSON Schema updates are necessary for {changes} files; run `make format` to update them."
            )
            return -1
        elif args.action == Action.Generate:
            logger.info(f"JSON Schema updated successfully for {changes} files.")
        else:
            raise NotImplementedError(f"Action {args.action} is not yet implemented")
    else:
        logger.info("No JSON Schema updates are necessary.")

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
