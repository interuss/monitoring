from implicitdict import ImplicitDict

from monitoring.deployment_manager.systems.dss.configuration import DSS
from monitoring.deployment_manager.systems.test.configuration import Test


class KubernetesCluster(ImplicitDict):
    name: str
    """Name of the Kubernetes cluster containing this deployment.

    Contained in the NAME column of the response to
    `kubectl config get-contexts`.
    """


class DeploymentSpec(ImplicitDict):
    cluster: KubernetesCluster | None
    """Definition of Kubernetes cluster containing this deployment."""

    test: Test | None
    """Test systems in this deployment."""

    dss: DSS | None
    """DSS instance in this deployment."""
