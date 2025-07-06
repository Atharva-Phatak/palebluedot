import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes.core.v1 import Namespace


def deploy_elasticsearch(
    depends_on: list[str],
    namespace: Namespace,
    k8s_provider: k8s.Provider,
):
    """
    Deploy Elasticsearch using Helm chart.

    Args:
        depends_on (list[str]): List of dependencies for the deployment.
        namespace (Namespace): Kubernetes namespace where Elasticsearch will be deployed.
        k8s_provider (k8s.Provider): Kubernetes provider configuration.

    Returns:
        Chart: The deployed Elasticsearch Helm chart resource.
    """
    eck_operator = Chart(
        "elasticsearch-operator",
        ChartOpts(
            chart="eck-operator",
            version="2.9.0",  # Use the latest stable version
            fetch_opts=FetchOpts(repo="https://helm.elastic.co"),
            namespace=namespace.metadata["name"],
        ),
        opts=pulumi.ResourceOptions(
            depends_on=depends_on,
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="20m"),
            replace_on_changes=["*"],  # Force replacement on conflicts
        ),
    )
    pulumi.export("elasticsearch_status", eck_operator.ready)
    return eck_operator
