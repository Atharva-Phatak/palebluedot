from applications.webhooks.metaflow_webhook import deploy_metaflow_webhook
from applications.webhooks.metaflow_webhook import deploy_metaflow_webhook_ingress
import pulumi_kubernetes as k8s


def deploy_metaflow_webhook_components(
    depends_on: list, k8s_provider: k8s.Provider, namespace: k8s.core.v1.Namespace
):
    deployment, service = deploy_metaflow_webhook(
        namespace=namespace, provider=k8s_provider, depends_on=depends_on
    )
    ingress = deploy_metaflow_webhook_ingress(
        provider=k8s_provider,
        namespace=namespace,
        depends_on=depends_on + [deployment, service],  # Handle None case
    )
    return ingress
