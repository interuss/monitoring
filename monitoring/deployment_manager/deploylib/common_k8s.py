from collections.abc import Callable
from typing import Any

from structlog import BoundLogger

from monitoring.deployment_manager.deploylib import comparisons


def get_resource(
    list_resources: Callable[[], Any],
    log: BoundLogger,
    resource_type: str,
    resource_name: str,
) -> Any | None:
    log.msg(f"Checking for existing {resource_type}", name=resource_name)
    resource_list = list_resources()
    matching_resources = [
        d for d in resource_list.items if d.metadata.name == resource_name
    ]
    if len(matching_resources) > 2:
        raise ValueError(
            f"Found {len(matching_resources)} {resource_type}s matching `{resource_name}`"
        )
    if not matching_resources:
        return None
    return matching_resources[0]


def upsert_resource(
    existing_resource: Any | None,
    target_resource: Any,
    log: BoundLogger,
    resource_type: str,
    create: Callable[[], Any],
    patch: Callable[[], Any],
) -> Any:
    if existing_resource is not None:
        if comparisons.specs_are_the_same(existing_resource, target_resource):
            log.msg(
                f"Existing {resource_type} does not need to be updated",
                name=existing_resource.metadata.name,
            )
            new_resource = existing_resource
        else:
            log.msg(f"Updating existing {resource_type}")
            new_resource = patch()
            log.msg(f"Updated {resource_type}", name=new_resource.metadata.name)
    else:
        log.msg(f"Creating new {resource_type}")
        new_resource = create()
        log.msg(f"Created {resource_type}", name=new_resource.metadata.name)
    return new_resource
