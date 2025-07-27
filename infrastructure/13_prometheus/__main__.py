from infrastructure.helper.namespace import create_namespace
from infrastructure.components.prometheus.deploy_prometheus import deploy_prometheus
from infrastructure.helper.provider import get_k8s_provider
import pulumi

provider = get_k8s_provider()
monitoring_namespace = create_namespace(
    provider=provider,
    namespace="monitoring",
)
# Deploy prometheus and grafana
prometheus_chart = deploy_prometheus(
    depends_on=[monitoring_namespace],
    provider=provider,
    namespace="monitoring",
)
pulumi.export("monitoring_namespace", monitoring_namespace.metadata["name"])
