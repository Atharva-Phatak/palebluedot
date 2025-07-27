import pulumi
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.components.grafana.deploy_grafana import deploy_grafana

pconfig = pulumi.Config()
# Load configuration
provider = get_k8s_provider()
namespace_name = pconfig.require("monitoring_namespace")

# deploy_grafana(
grafana_chart = deploy_grafana(
    provider=provider, depends_on=[], namespace=namespace_name
)
