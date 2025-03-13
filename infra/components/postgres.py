import pulumi_kubernetes as k8s
import pulumi


def deploy_postgres(provider: k8s.Provider, depends_on: list = None):
    namespace = "flyte"
    # Persistent Volume
    pv = k8s.core.v1.PersistentVolume(
        "flyte-db-storage",
        metadata={"name": "flyte-db-storage"},
        spec={
            "storageClassName": "manual",
            "accessModes": ["ReadWriteOnce"],
            "capacity": {"storage": "1Gi"},
            "volumeMode": "Filesystem",
            "hostPath": {"path": "/home/atharva/Desktop/minikube_path/postgres"},
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )

    # Persistent Volume Claim
    pvc = k8s.core.v1.PersistentVolumeClaim(
        "postgresql-pvc",
        metadata={"name": "postgresql-pvc", "namespace": namespace},
        spec={
            "accessModes": ["ReadWriteOnce"],
            "resources": {"requests": {"storage": "1Gi"}},
            "storageClassName": "manual",
            "volumeName": pv.metadata["name"],
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on + [pv]),
    )

    # PostgreSQL Deployment
    deployment = k8s.apps.v1.Deployment(
        "postgres",
        metadata={"name": "postgres", "namespace": namespace},
        spec={
            "selector": {"matchLabels": {"app": "postgres"}},
            "template": {
                "metadata": {"labels": {"app": "postgres"}},
                "spec": {
                    "containers": [
                        {
                            "name": "postgres",
                            "image": "postgres:14.17-bookworm",
                            "imagePullPolicy": "IfNotPresent",
                            "env": [
                                {"name": "POSTGRES_USER", "value": "postgres"},
                                {"name": "POSTGRES_PASSWORD", "value": "postgres"},
                                {"name": "POSTGRES_DB", "value": "flyteadmin"},
                            ],
                            "ports": [{"containerPort": 5432}],
                            "volumeMounts": [
                                {
                                    "name": "postgres-storage",
                                    "mountPath": "/home/atharva/Desktop/minikube_path/postgres",
                                }
                            ],
                        }
                    ],
                    "volumes": [
                        {
                            "name": "postgres-storage",
                            "persistentVolumeClaim": {
                                "claimName": pvc.metadata["name"]
                            },
                        }
                    ],
                },
            },
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on + [pvc]),
    )

    # PostgreSQL Service
    service = k8s.core.v1.Service(
        "postgres-service",
        metadata={"name": "postgres", "namespace": namespace},
        spec={
            "ports": [{"port": 5432, "targetPort": 5432}],
            "selector": {"app": "postgres"},
        },
        opts=pulumi.ResourceOptions(
            provider=provider, depends_on=depends_on + [deployment]
        ),
    )

    return service
