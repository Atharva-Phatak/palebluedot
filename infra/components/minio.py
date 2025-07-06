from applications.persistent_claims.pv import deploy_persistent_volume_claims
from applications.minio.buckets import deploy_minio_buckets
from applications.minio.minio import deploy_minio
from pulumi_kubernetes.core.v1 import Namespace
import pulumi_kubernetes as k8s


def deploy_minio_component(
    cfg,
    k8s_provider: k8s.Provider,
    namespace: Namespace,
    depends_on: list,
):

    minio_pv_claim = deploy_persistent_volume_claims(
        namespace=namespace,
        provider=k8s_provider,
        pv_name=cfg.pv_name,
        pvc_name=cfg.pvc_name,
        storage_capacity=cfg.mk_storage_capacity,
        storage_path=cfg.storage_path,
        depends_on=depends_on,
    )
    # Deploy MinIO
    minio_chart = deploy_minio(
        provider=k8s_provider,
        namespace=namespace,
        ingress_host=cfg.minio_ingress_host,
        deployment_name=cfg.minio_deployment_name,
        service_name=cfg.minio_service_name,
        pvc_name=minio_pv_claim.metadata["name"],
        depends_on=depends_on + [minio_pv_claim],
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
        depends_on=depends_on + [minio_chart, minio_pv_claim],
        buckets=[cfg.data_bucket, cfg.zenml_bucket],
        ingress_host=cfg.minio_ingress_host,
    )
    return minio_chart
