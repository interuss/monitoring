from typing import cast

import kubernetes

from monitoring.deployment_manager.infrastructure import Context, deployment_action


@deployment_action("list_pods")
def list_pods(context: Context):
    """List all Kubernetes pods"""
    if not context.clients:
        raise ValueError("Clients not initialized in context")
    ret = cast(
        kubernetes.client.V1PodList,
        context.clients.core.list_pod_for_all_namespaces(watch=False),
    )
    msg = "\n".join(
        [
            f"{i.status.pod_ip}\t{i.metadata.namespace}\t{i.metadata.name}"
            for i in ret.items or []
        ]
    )
    context.log.msg("Pods:\n" + msg)


@deployment_action("list_ingress_controllers")
def list_ingress_controllers(context: Context):
    """List all available ingress controllers"""
    if not context.clients:
        raise ValueError("Clients not initialized in context")
    class_list = cast(
        kubernetes.client.V1IngressClassList,
        context.clients.networking.list_ingress_class(),
    )
    msg = "\n".join(
        [
            f"{c.metadata.name}\t{c.spec.controller}\t{c.spec.parameters}"
            for c in class_list.items or []
        ]
    )
    context.log.msg("Ingress controllers:\n" + msg)
