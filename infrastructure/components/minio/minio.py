import pulumi
import pulumi_kubernetes as k8s
from infrastructure.helper.infisical_client import get_infiscal_sdk
from infrastructure.components.persistent_claims.pv import (
    deploy_persistent_volume_claims,
)
import pulumi_minio as pm
from infrastructure.helper.secrets import generate_minio_secret, create_k8s_aws_secret
from infrastructure.helper.constants import SecretNames, InfrastructureConfig


def get_minio_secret(
    access_key_identifier: str,
    secret_key_identifier: str,
    project_id: str,
    environment_slug: str,
):
    client = get_infiscal_sdk()
    minio_access_key = client.secrets.get_secret_by_name(
        secret_name=access_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
        secret_path="/",
    )
    minio_secret_key = client.secrets.get_secret_by_name(
        secret_name=secret_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
        secret_path="/",
    )
    return minio_access_key.secretValue, minio_secret_key.secretValue


def deploy_minio(
    namespace: str,
    provider: k8s.Provider,
    deployment_name: str,
    service_name: str,
    ingress_host: str,
    pvc_name: str,
    access_key_identifier: str,
    secret_key_identifier: str,
    project_id: str,
    environment_slug: str,
    depends_on: list = None,
):
    if depends_on is None:
        depends_on = []

    minio_access_key, minio_secret_key = get_minio_secret(
        access_key_identifier=access_key_identifier,
        secret_key_identifier=secret_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
    )
    # Create a Deployment
    minio_deployment = k8s.apps.v1.Deployment(
        "minio-deployment",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=deployment_name,
            namespace=namespace,
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={"app.kubernetes.io/name": "minio"}
            ),
            strategy=k8s.apps.v1.DeploymentStrategyArgs(type="Recreate"),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    labels={"app.kubernetes.io/name": "minio"}
                ),
                spec=k8s.core.v1.PodSpecArgs(
                    host_network=True,
                    restart_policy="Always",
                    volumes=[
                        k8s.core.v1.VolumeArgs(
                            name="storage",
                            persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                                claim_name=pvc_name
                            ),
                        )
                    ],
                    containers=[
                        k8s.core.v1.ContainerArgs(
                            name="minio",
                            image="minio/minio:latest",
                            args=["server", "/data"],
                            resources=k8s.core.v1.ResourceRequirementsArgs(
                                limits={"cpu": "100m", "memory": "1Gi"},
                                requests={"cpu": "10m", "memory": "512Mi"},
                            ),
                            env=[
                                k8s.core.v1.EnvVarArgs(
                                    name="MINIO_ACCESS_KEY", value=minio_access_key
                                ),
                                k8s.core.v1.EnvVarArgs(
                                    name="MINIO_SECRET_KEY", value=minio_secret_key
                                ),
                            ],
                            ports=[k8s.core.v1.ContainerPortArgs(container_port=9000)],
                            volume_mounts=[
                                k8s.core.v1.VolumeMountArgs(
                                    name="storage",
                                    mount_path="/data",
                                )
                            ],
                        )
                    ],
                ),
            ),
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )

    # Create a Service
    minio_service = k8s.core.v1.Service(
        "minio-service",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=service_name,
            namespace=namespace,
            labels={"app.kubernetes.io/name": "minio"},
        ),
        spec=k8s.core.v1.ServiceSpecArgs(
            selector={"app.kubernetes.io/name": "minio"},
            ports=[
                k8s.core.v1.ServicePortArgs(
                    name="minio", protocol="TCP", port=9000, target_port=9000
                )
            ],
            type="ClusterIP",
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[minio_deployment]),
    )

    # Create an Ingress
    minio_ingress = k8s.networking.v1.Ingress(
        "minio-ingress",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="minio-ingress",
            namespace=namespace,  # Added namespace
            annotations={
                "nginx.ingress.kubernetes.io/rewrite-target": "/",
                "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                "nginx.ingress.kubernetes.io/proxy-body-size": "64m",
                "nginx.ingress.kubernetes.io/proxy-connect-timeout": "300",
                "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
            },
        ),
        spec=k8s.networking.v1.IngressSpecArgs(
            rules=[
                k8s.networking.v1.IngressRuleArgs(
                    host=ingress_host,
                    http=k8s.networking.v1.HTTPIngressRuleValueArgs(
                        paths=[
                            k8s.networking.v1.HTTPIngressPathArgs(
                                path="/",
                                path_type="Prefix",
                                backend=k8s.networking.v1.IngressBackendArgs(
                                    service=k8s.networking.v1.IngressServiceBackendArgs(
                                        name=service_name,
                                        port=k8s.networking.v1.ServiceBackendPortArgs(
                                            number=9000
                                        ),
                                    )
                                ),
                            )
                        ]
                    ),
                )
            ]
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            custom_timeouts=pulumi.CustomTimeouts(create="20m"),
            depends_on=[minio_service],
        ),
    )

    return minio_ingress


def deploy_minio_buckets(
    depends_on: list,
    buckets: list[str],
    access_key_identifier: str,
    secret_key_identifier: str,
    infiscal_project_id: str,
    environment_slug: str,
    ingress_host: str = None,
):
    minio_access_key, minio_secret_key = get_minio_secret(
        access_key_identifier=access_key_identifier,
        secret_key_identifier=secret_key_identifier,
        project_id=infiscal_project_id,
        environment_slug=environment_slug,
    )
    # Create a bucket
    minio_provider = pm.Provider(
        "minio-provider",
        minio_server=ingress_host,
        minio_user=minio_access_key,
        minio_password=minio_secret_key,
    )
    for bucket in buckets:
        pm.S3Bucket(
            bucket,
            bucket=bucket,
            opts=pulumi.ResourceOptions(depends_on=depends_on, provider=minio_provider),
        )


def deploy_minio_components(
    cfg: InfrastructureConfig,
    provider: k8s.Provider,
    namespace: str,
    depends_on: list = None,
):
    depends_on = [] if depends_on is None else depends_on
    generate_minio_secret(
        project_id=cfg.infiscal_project_id,
        environment_slug="dev",
    )
    k8s_secret = create_k8s_aws_secret(
        provider=provider,
        namespace=namespace,
        project_id=cfg.infiscal_project_id,
        depends_on=depends_on,
    )
    minio_pv_claim = deploy_persistent_volume_claims(
        namespace=namespace,
        provider=provider,
        pv_name=cfg.pv_name,
        pvc_name=cfg.pvc_name,
        storage_capacity=cfg.minio_storage_capacity,
        storage_path=cfg.storage_path,
        depends_on=depends_on,
    )
    # Deploy MinIO
    minio_chart = deploy_minio(
        provider=provider,
        namespace=namespace,
        ingress_host=cfg.minio_ingress_host,
        deployment_name=cfg.minio_deployment_name,
        service_name=cfg.minio_service_name,
        pvc_name=minio_pv_claim.metadata["name"],
        depends_on=depends_on + [minio_pv_claim] + [k8s_secret],
        access_key_identifier=SecretNames.MINIO_ACCESS_KEY.value,
        secret_key_identifier=SecretNames.MINIO_SECRET_KEY.value,
        project_id=cfg.infiscal_project_id,
        environment_slug="dev",
    )
    # Deploy MinIO buckets
    deploy_minio_buckets(
        access_key_identifier=SecretNames.MINIO_ACCESS_KEY.value,
        secret_key_identifier=SecretNames.MINIO_SECRET_KEY.value,
        infiscal_project_id=cfg.infiscal_project_id,
        environment_slug="dev",
        depends_on=depends_on + [minio_chart, minio_pv_claim],
        buckets=[cfg.data_bucket, cfg.zenml_bucket],
        ingress_host=cfg.minio_ingress_host,
    )
    return minio_chart
