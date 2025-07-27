import pulumi
import pulumi_kubernetes as k8s


def deploy_persistent_volume_claims(
    pv_name: str,
    pvc_name: str,
    namespace: str,
    provider: k8s.Provider,
    storage_capacity: str,
    storage_path: str,
    storage_class_name: str = "standard",  # ✅ Use a unique storage class
    depends_on: list = None,
):
    depends_on = depends_on or []

    # Create a Persistent Volume
    pv = k8s.core.v1.PersistentVolume(
        pv_name,
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=pv_name,
            labels={
                "type": "manual-storage",
                "pv-name": pv_name,  # Unique identifier
            },
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
            namespace=namespace,
        ),
        spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={
                    "pv-name": pv_name,
                }
            ),
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
