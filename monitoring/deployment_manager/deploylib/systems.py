from typing import Any

from kubernetes.client import V1Deployment, V1Ingress, V1Namespace, V1Service
from structlog import BoundLogger

from monitoring.deployment_manager.deploylib import (
    deployments,
    ingresses,
    namespaces,
    services,
)
from monitoring.deployment_manager.infrastructure import Clients


def upsert_resources(
    target_resources: list[Any],
    namespace: V1Namespace,
    clients: Clients,
    log: BoundLogger,
) -> None:
    for target_resource in target_resources:
        if target_resource.__class__ == V1Deployment:
            deployments.upsert(clients.apps, log, namespace, target_resource)
        elif target_resource.__class__ == V1Ingress:
            ingresses.upsert(clients.networking, log, namespace, target_resource)
        elif target_resource.__class__ == V1Namespace:
            namespaces.upsert(clients.core, log, target_resource)
        elif target_resource.__class__ == V1Service:
            services.upsert(clients.core, log, namespace, target_resource)
        else:
            raise NotImplementedError(
                f"Upserting {target_resource.__class__} is not yet supported"
            )


def get_resources(
    target_resources: list[Any],
    namespace: V1Namespace,
    clients: Clients,
    log: BoundLogger,
    cluster_name: str,
) -> list[Any]:
    existing_resources = []
    for target_resource in target_resources:
        if target_resource.__class__ == V1Deployment:
            existing_resource = deployments.get(
                clients.apps, log, namespace, target_resource
            )
        elif target_resource.__class__ == V1Ingress:
            existing_resource = ingresses.get(
                clients.networking, log, namespace, target_resource
            )
        elif target_resource.__class__ == V1Namespace:
            existing_resource = namespaces.get(clients.core, log, target_resource)
        elif target_resource.__class__ == V1Service:
            existing_resource = services.get(
                clients.core, log, namespace, target_resource
            )
        else:
            raise NotImplementedError(
                f"Getting {target_resource.__class__} is not yet supported"
            )

        if existing_resource is None:
            log.warn(
                f"No existing {target_resource.metadata.name} {target_resource.__class__.__name__} found in `{namespace.metadata.name}` namespace of `{cluster_name}` cluster"
            )
        existing_resources.append(existing_resource)
    return existing_resources


def delete_resources(
    existing_resources: list[Any],
    namespace: V1Namespace,
    clients: Clients,
    log: BoundLogger,
):
    for existing_resource in existing_resources:
        if existing_resource is None:
            pass
        elif existing_resource.__class__ == V1Deployment:
            log.msg("Deleting deployment")
            status = clients.apps.delete_namespaced_deployment(
                name=existing_resource.metadata.name, namespace=namespace.metadata.name
            )
            log.msg("Deployment deleted", message=status.message)
        elif existing_resource.__class__ == V1Ingress:
            log.msg("Deleting ingress")
            status = clients.networking.delete_namespaced_ingress(
                name=existing_resource.metadata.name, namespace=namespace.metadata.name
            )
            log.msg("Ingress deleted", message=status.message)
        elif existing_resource.__class__ == V1Namespace:
            log.msg("Deleting namespace")
            status = clients.core.delete_namespace(name=namespace.metadata.name)
            log.msg("Namespace deleted", name=status.message)
        elif existing_resource.__class__ == V1Service:
            log.msg("Deleting service")
            svc = clients.core.delete_namespaced_service(
                name=existing_resource.metadata.name, namespace=namespace.metadata.name
            )
            log.msg("Service deleted", message=svc.metadata.name)
        else:
            raise NotImplementedError(
                f"Deleting {existing_resource.__class__} is not yet supported"
            )
