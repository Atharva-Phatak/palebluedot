from infrastructure.helper.secrets import create_mistral_api_secret, create_slack_secret
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config
import pulumi

cfg = load_config()
provider = get_k8s_provider()
pconfig = pulumi.Config()
namespace_name = pconfig.require("metaflow_namespace")


_ = create_slack_secret(
    namespace=namespace_name,
    project_id=cfg.infiscal_project_id,
    depends_on=[],
    k8s_provider=provider,
)

_ = create_mistral_api_secret(
    namespace=namespace_name,
    depends_on=[],
    project_id=cfg.infiscal_project_id,
    k8s_provider=provider,
    environment_slug="dev",
)
