from components.minikube import start_minikube
from components.postgres import deploy_postgres
from components.minio import deploy_minio
from components.provider import get_k8s_provider
from components.namespace import create_namespace
from components.flyte import deploy_flyte
from components.buckets import deploy_minio_buckets

# Ensure Minikube starts before deploying resources
minikube_start = start_minikube()
provider = get_k8s_provider(depends_on=[minikube_start])
flyte_namespace = create_namespace(
    provider=provider, namespace="flyte-namespace", depends_on=[minikube_start]
)
# Deploy PostgreSQL
postgres_service = deploy_postgres(provider=provider, depends_on=[flyte_namespace])

# Deploy MinIO
minio_ingress = deploy_minio(
    provider=provider, namespace=flyte_namespace, depends_on=[flyte_namespace]
)
deploy_minio_buckets(
    depends_on=[minio_ingress, minikube_start],
    minio_ingress=minio_ingress,
)
deploy_flyte = deploy_flyte(
    namespace=flyte_namespace,
    provider=provider,
    depends_on=[postgres_service, minio_ingress, flyte_namespace, minikube_start],
)
