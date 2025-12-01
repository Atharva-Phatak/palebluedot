from infrastructure.helper.secrets import (
    create_k8s_slack_secret,
    create_k8s_wandb_secret,
)
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config
import pulumi

cfg = load_config()
provider = get_k8s_provider()
pconfig = pulumi.Config()
namespace_name = pconfig.require("namespace")


_ = create_k8s_slack_secret(
    namespace=namespace_name,
    project_id=cfg.infiscal_project_id,
    depends_on=[],
    k8s_provider=provider,
)

_ = create_k8s_wandb_secret(
    namespace=namespace_name,
    project_id=cfg.infiscal_project_id,
    depends_on=[],
    k8s_provider=provider,
)
