from applications.persistent_claims.pv import deploy_persistent_volume_claims
import pulumi_kubernetes as k8s
from omegaconf import DictConfig
from pulumi_kubernetes.core.v1 import Namespace


def deploy_models_pvc(
    cfg: DictConfig,
    namespace: Namespace,
    k8s_provider: k8s.Provider,
    depends_on: list,
):
    """Deploys Persistent Volume Claims for models."""
    model_pv_claims = deploy_persistent_volume_claims(
        namespace=namespace,
        provider=k8s_provider,
        pv_name=cfg.model_pv_name,
        pvc_name=cfg.model_pvc_name,
        storage_capacity=cfg.model_storage_capacity,
        storage_path=cfg.model_storage_path,
        depends_on=depends_on,
    )
    return model_pv_claims
