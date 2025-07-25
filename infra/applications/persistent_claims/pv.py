import pulumi
import pulumi_kubernetes as k8s


def deploy_persistent_volume_claims(
    pv_name: str,
    pvc_name: str,
    namespace: k8s.core.v1.Namespace,
    provider: k8s.Provider,
    storage_capacity: str,
    storage_path: str,
    storage_class_name: str = "manual-model-storage",  # ✅ Use a unique storage class
    depends_on: list = None,
):
    depends_on = depends_on or []

    # Create a Persistent Volume
    pv = k8s.core.v1.PersistentVolume(
        pv_name,
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=pv_name,
        ),
        spec=k8s.core.v1.PersistentVolumeSpecArgs(
            capacity={"storage": storage_capacity},
            access_modes=["ReadWriteOnce"],
            persistent_volume_reclaim_policy="Retain",
            volume_mode="Filesystem",
            storage_class_name=storage_class_name,
            host_path=k8s.core.v1.HostPathVolumeSourceArgs(path=storage_path),
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )

    # Create a Persistent Volume Claim that binds to the above PV
    pvc = k8s.core.v1.PersistentVolumeClaim(
        pvc_name,
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=pvc_name,
            namespace=namespace.metadata["name"],
        ),
        spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
            access_modes=["ReadWriteOnce"],
            resources=k8s.core.v1.VolumeResourceRequirementsArgs(
                requests={"storage": storage_capacity}
            ),
            storage_class_name=storage_class_name,
            volume_mode="Filesystem",
            volume_name=pv.metadata.name,  # ✅ Explicitly bind to your PV
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[pv] + depends_on),
    )
    return pvc
