import pulumi
import pulumi_kubernetes as k8s

# Constants (hardcoded from the variables in the Terraform code)
minio_pv_name = "minio-pv"
minio_pvc_name = "minio-pvc"
minio_storage = "10Gi"
minio_storage_path = "/home/atharvaphatak/Desktop/minikube_path/minio"
minio_deployment_name = "minio"
minio_service_name = "minio"
minio_access_key = "minio@1234"
minio_secret_key = "minio@local1234"
minio_ingress_host = "fsml-minio.info"


def deploy_minio(
    namespace: k8s.core.v1.Namespace, provider: k8s.Provider, depends_on: list = None
):
    if depends_on is None:
        depends_on = []

    # Create a Persistent Volume
    minio_pv = k8s.core.v1.PersistentVolume(
        "minio-pv",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=minio_pv_name,
            namespace=namespace.metadata["name"],
        ),
        spec=k8s.core.v1.PersistentVolumeSpecArgs(
            capacity={"storage": minio_storage},
            access_modes=["ReadWriteOnce"],
            persistent_volume_reclaim_policy="Retain",
            storage_class_name="manual",
            volume_mode="Filesystem",
            # Fixed: Use host_path directly instead of persistent_volume_source
            host_path=k8s.core.v1.HostPathVolumeSourceArgs(path=minio_storage_path),
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )

    # Create a Persistent Volume Claim
    minio_pvc = k8s.core.v1.PersistentVolumeClaim(
        "minio-pvc",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=minio_pvc_name,
            namespace=namespace.metadata["name"],
        ),
        spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
            access_modes=["ReadWriteOnce"],
            resources=k8s.core.v1.ResourceRequirementsArgs(
                requests={"storage": minio_storage}
            ),
            storage_class_name="manual",
            volume_mode="Filesystem",
            volume_name=minio_pv_name,
        ),
        opts=pulumi.ResourceOptions(
            provider=provider, depends_on=[minio_pv] + depends_on
        ),
    )

    # Create a Deployment
    minio_deployment = k8s.apps.v1.Deployment(
        "minio-deployment",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=minio_deployment_name,
            namespace=namespace.metadata["name"],
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
                                claim_name=minio_pvc_name
                            ),
                        )
                    ],
                    containers=[
                        k8s.core.v1.ContainerArgs(
                            name="minio",
                            image="minio/minio:latest",
                            args=["server", "/data"],
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
        opts=pulumi.ResourceOptions(
            provider=provider, depends_on=[minio_pvc] + depends_on
        ),
    )

    # Create a Service
    minio_service = k8s.core.v1.Service(
        "minio-service",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=minio_service_name,
            namespace=namespace.metadata["name"],
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
            namespace=namespace.metadata["name"],  # Added namespace
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
                    host=minio_ingress_host,
                    http=k8s.networking.v1.HTTPIngressRuleValueArgs(
                        paths=[
                            k8s.networking.v1.HTTPIngressPathArgs(
                                path="/",
                                path_type="Prefix",
                                backend=k8s.networking.v1.IngressBackendArgs(
                                    service=k8s.networking.v1.IngressServiceBackendArgs(
                                        name=minio_service_name,
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
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=[minio_service],
        ),
    )

    return minio_ingress
