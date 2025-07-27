from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config
import pulumi
from infrastructure.components.argo.argo_workflows.deploy_argo_workflows import (
    deploy_argo_workflows,
)

provider = get_k8s_provider()
config = load_config()
pconfig = pulumi.Config()
namespace_name = pconfig.require("metaflow_namespace")

argo_worflows = deploy_argo_workflows(
    k8s_provider=provider, namespace=namespace_name, depends_on=[]
)
