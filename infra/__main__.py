from components.k8s.minikube import start_minikube
from components.k8s.provider import get_k8s_provider
from components.k8s.namespace import create_namespace
from components.minio.minio import deploy_minio
from components.minio.buckets import deploy_minio_buckets
from components.persistent_claims.pv import deploy_persistent_volume_claims
from components.secret_manager.secrets import create_aws_secret
from components.sql.mysql import deploy_mysql
from components.zenml.zenml import deploy_zenml
from helper.constant import Constants

# Ensure Minikube starts before deploying resources
minikube_start = start_minikube()
k8s_provider = get_k8s_provider(depends_on=[minikube_start])
zenml_namespace = create_namespace(
    provider=k8s_provider, namespace="zenml", depends_on=[minikube_start]
)
# nvidia_namespace = create_namespace(
#    provider=k8s_provider, namespace="nvidia-gpu-operator", depends_on=[minikube_start]
# )


# Deploy MySQL
# Todo: Use the zenml namespace created above
mysql_service = deploy_mysql(
    provider=k8s_provider,
    namespace="zenml",
    depends_on=[minikube_start, zenml_namespace],
)
minio_pv_claim = deploy_persistent_volume_claims(
    namespace=zenml_namespace,
    provider=k8s_provider,
    pv_name=Constants.pv_name,
    pvc_name=Constants.pvc_name,
    storage_capacity=Constants.mk_storage_capacity,
    storage_path=Constants.storage_path,
    depends_on=[minikube_start, zenml_namespace],
)
model_pv_claims = deploy_persistent_volume_claims(
    namespace=zenml_namespace,
    provider=k8s_provider,
    pv_name=Constants.model_pv_name,
    pvc_name=Constants.model_pvc_name,
    storage_capacity=Constants.model_storage_capacity,
    storage_path=Constants.model_storage_path,
    depends_on=[minikube_start, zenml_namespace],
)
create_aws_secret(
    provider=k8s_provider,
    namespace="zenml",
    depends_on=[minikube_start, zenml_namespace],
)
# Deploy MinIO
minio_ingress = deploy_minio(
    provider=k8s_provider,
    namespace=zenml_namespace,
    depends_on=[zenml_namespace, minio_pv_claim],
)
deploy_minio_buckets(
    depends_on=[minio_ingress, minikube_start],
)
zenml_resource = deploy_zenml(
    depends_on=[minikube_start, zenml_namespace, model_pv_claims, mysql_service],
    k8s_provider=k8s_provider,
    namespace="zenml",
)
# Deploy NVIDIA GPU Operator after ZenML
# nvidia_gpu_operator = deploy_nvidia_gpu_operator(
#    namespace=nvidia_namespace,
#    provider=k8s_provider,
#    depends_on=[
#        minikube_start,
#        pv_claims,
#        minio_ingress,
#        mysql_service,
#        zenml_resource,
#    ],
# )
