import pulumi
from infrastructure.components.zenml.deploy_zenml import deploy_zenml
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config


provider = get_k8s_provider()
pconfig = pulumi.Config()
namespace_name = pconfig.require("namespace")
config = load_config()
zenml_chart = deploy_zenml(
    depends_on=[],
    k8s_provider=provider,
    namespace=namespace_name,
    infiscal_project_id=config.infiscal_project_id,
    environment_slug="dev",
)
