from omegaconf import OmegaConf
from components.k8s.minikube import start_minikube
from components.k8s.provider import get_k8s_provider
from components.k8s.namespace import create_namespace
from components.minio.minio import deploy_minio
from components.minio.buckets import deploy_minio_buckets
from components.persistent_claims.pv import deploy_persistent_volume_claims
from components.secret_manager.secrets import create_aws_secret
from components.sql.mysql import deploy_mysql
from components.zenml.zenml import deploy_zenml


def load_config():
    cfg = OmegaConf.load("configs/config.yaml")
    return cfg


# load config and constants in the yaml
cfg = load_config()
# Ensure Minikube starts before deploying resources
minikube_start = start_minikube(
    n_cpus=cfg.minikube_cpus,
    memory=cfg.minikube_memory,
    addons=cfg.minikube_addons,
    gpus=cfg.minikube_gpus,
    disk_size=cfg.minikube_disk_size,
)

k8s_provider = get_k8s_provider(depends_on=[minikube_start])
zenml_namespace = create_namespace(
    provider=k8s_provider, namespace="zenml", depends_on=[minikube_start]
)
create_aws_secret(
    provider=k8s_provider,
    namespace="zenml",
    depends_on=[minikube_start, zenml_namespace],
    infiscal_project_id=cfg.infiscal_project_id,
)
# Deploy MySQL service required for ZenML
mysql_service = deploy_mysql(
    provider=k8s_provider,
    namespace="zenml",
    depends_on=[minikube_start, zenml_namespace],
    sql_host_path=cfg.sql_host_path,
)
# Deploy Persistent Volume Claims
minio_pv_claim = deploy_persistent_volume_claims(
    namespace=zenml_namespace,
    provider=k8s_provider,
    pv_name=cfg.pv_name,
    pvc_name=cfg.pvc_name,
    storage_capacity=cfg.mk_storage_capacity,
    storage_path=cfg.storage_path,
    depends_on=[minikube_start, zenml_namespace],
)
model_pv_claims = deploy_persistent_volume_claims(
    namespace=zenml_namespace,
    provider=k8s_provider,
    pv_name=cfg.model_pv_name,
    pvc_name=cfg.model_pvc_name,
    storage_capacity=cfg.model_storage_capacity,
    storage_path=cfg.model_storage_path,
    depends_on=[minikube_start, zenml_namespace],
)

# Deploy MinIO
minio_ingress = deploy_minio(
    provider=k8s_provider,
    namespace=zenml_namespace,
    ingress_host=cfg.minio_ingress_host,
    deployment_name=cfg.minio_deployment_name,
    service_name=cfg.minio_service_name,
    pvc_name=minio_pv_claim.metadata["name"],
    depends_on=[zenml_namespace, minio_pv_claim],
    access_key_identifier="minio_access_key",
    secret_key_identifier="minio_secret_key",
    project_id=cfg.infiscal_project_id,
    environment_slug="dev",
)
# Deploy MinIO buckets
deploy_minio_buckets(
    access_key_identifier="minio_access_key",
    secret_key_identifier="minio_secret_key",
    infiscal_project_id=cfg.infiscal_project_id,
    environment_slug="dev",
    depends_on=[minio_ingress, minikube_start],
    buckets=[cfg.data_bucket, cfg.zenml_bucket],
    ingress_host=cfg.minio_ingress_host,
)
# Deploy ZenML
zenml_resource = deploy_zenml(
    depends_on=[minikube_start, zenml_namespace, model_pv_claims, mysql_service],
    k8s_provider=k8s_provider,
    namespace="zenml",
)
