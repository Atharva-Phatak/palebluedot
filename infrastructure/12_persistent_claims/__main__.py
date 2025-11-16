from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config
from infrastructure.components.persistent_claims.pv import (
    deploy_persistent_volume_claims,
)
import pulumi

provider = get_k8s_provider()
cfg = load_config()
pconfig = pulumi.Config()
namespace_name = pconfig.require("namespace")
# Deploy pv that has models
model_pv_claims = deploy_persistent_volume_claims(
    namespace=namespace_name,
    provider=provider,
    pv_name=cfg.model_pv_name,
    pvc_name=cfg.model_pvc_name,
    storage_capacity=cfg.model_storage_capacity,
    storage_path=cfg.model_storage_path,
)
