from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config
from infrastructure.components.webhooks.metaflow_webhook import deploy_metaflow_webhook
import pulumi

provider = get_k8s_provider()
config = load_config()
pconfig = pulumi.Config()
namespace_name = pconfig.require("metaflow_namespace")
deploy_metaflow_webhook(
    provider=provider,
    namespace=namespace_name,
)
