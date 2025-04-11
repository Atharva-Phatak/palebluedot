import pulumi
import pulumi_kubernetes as k8s
from helper.constant import Constants


def deploy_persistent_volume_claims(
    namespace: k8s.core.v1.Namespace, provider: k8s.Provider, depends_on: list = None
):
    # Create a Persistent Volume
    pv = k8s.core.v1.PersistentVolume(
        "minio-pv",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=Constants.pv_name,
            namespace=namespace.metadata["name"],
        ),
        spec=k8s.core.v1.PersistentVolumeSpecArgs(
            capacity={"storage": Constants.storage_capacity},
            access_modes=["ReadWriteOnce"],
            persistent_volume_reclaim_policy="Retain",
            storage_class_name="manual",
            volume_mode="Filesystem",
            # Fixed: Use host_path directly instead of persistent_volume_source
            host_path=k8s.core.v1.HostPathVolumeSourceArgs(path=Constants.storage_path),
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )

    # Create a Persistent Volume Claim
    pvc = k8s.core.v1.PersistentVolumeClaim(
        "minio-pvc",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=Constants.pvc_name,
            namespace=namespace.metadata["name"],
        ),
        spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
            access_modes=["ReadWriteOnce"],
            resources=k8s.core.v1.VolumeResourceRequirementsArgs(
                requests={"storage": Constants.storage_capacity}
            ),
            storage_class_name="manual",
            volume_mode="Filesystem",
            volume_name=pv.metadata.name,
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[pv] + depends_on),
    )
    return pvc
