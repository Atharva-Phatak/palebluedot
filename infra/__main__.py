from components.minikube import start_minikube
from components.mysql import deploy_mysql
from components.minio import deploy_minio
from components.provider import get_k8s_provider
from components.namespace import create_namespace
from components.buckets import deploy_minio_buckets
from components.zenml import deploy_zenml

# Ensure Minikube starts before deploying resources
minikube_start = start_minikube()
k8s_provider = get_k8s_provider(depends_on=[minikube_start])
zenml_namespace = create_namespace(
    provider=k8s_provider, namespace="zenml", depends_on=[minikube_start]
)
# Deploy MySQL
mysql_service = deploy_mysql(
    provider=k8s_provider,
    namespace="zenml",
    depends_on=[minikube_start, zenml_namespace],
)
# Deploy MinIO
minio_ingress = deploy_minio(
    provider=k8s_provider, namespace=zenml_namespace, depends_on=[zenml_namespace]
)
deploy_minio_buckets(
    depends_on=[minio_ingress, minikube_start],
    minio_ingress=minio_ingress,
)
deploy_zenml(
    depends_on=[minikube_start, zenml_namespace, mysql_service],
    k8s_provider=k8s_provider,
    namespace="zenml",
)
