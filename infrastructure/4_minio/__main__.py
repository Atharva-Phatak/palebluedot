from infrastructure.helper.config import load_config
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.components.minio.minio import deploy_minio_components
import pulumi

config = load_config()
provider = get_k8s_provider()
pconfig = pulumi.Config()
namespace_name = pconfig.require("metaflow_namespace")
deploy_minio_components(
    cfg=config,
    provider=provider,
    namespace=namespace_name,
)
