import pulumi_kubernetes as k8s
import pulumi
import base64
from helper.constant import Constants


def deploy_mysql(
    provider: k8s.Provider,
    namespace: str,
    depends_on: list = None,
) -> k8s.core.v1.Service:
    # Persistent Volume
    pv = k8s.core.v1.PersistentVolume(
        "zenml-db-storage",
        metadata={"name": "zenml-db-storage", "namespace": namespace},
        spec={
            "storageClassName": "manual",
            "accessModes": ["ReadWriteOnce"],
            "capacity": {"storage": "5Gi"},
            "volumeMode": "Filesystem",
            "hostPath": {"path": Constants.sql_host_path},
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )

    # Persistent Volume Claim
    pvc = k8s.core.v1.PersistentVolumeClaim(
        "mysql-pvc",
        metadata={"name": "mysql-pvc", "namespace": namespace},
        spec={
            "accessModes": ["ReadWriteOnce"],
            "resources": {"requests": {"storage": "1Gi"}},
            "storageClassName": "manual",
            "volumeName": pv.metadata["name"],
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on + [pv]),
    )
    mysql_secret = k8s.core.v1.Secret(
        "mysql-secret",
        metadata={
            "name": "mysql-secret",
            "namespace": namespace,
        },
        type="Opaque",
        # Use 'data' with base64 encoded values instead of 'string_data'
        data={
            "mysql-root-password": base64.b64encode(b"root").decode("utf-8"),
            "mysql-user": base64.b64encode(b"zenml").decode("utf-8"),
            "mysql-password": base64.b64encode(b"zenml").decode("utf-8"),
        },
        opts=pulumi.ResourceOptions(provider=provider),
    )

    # MySQL Deployment with Secret references
    deployment = k8s.apps.v1.Deployment(
        "mysql",
        metadata={
            "name": "mysql",
            "namespace": namespace,
            "labels": {"app.kubernetes.io/name": "mysql"},
        },
        spec={
            "selector": {"matchLabels": {"app.kubernetes.io/name": "mysql"}},
            "template": {
                "metadata": {"labels": {"app.kubernetes.io/name": "mysql"}},
                "spec": {
                    "containers": [
                        {
                            "name": "mysql",
                            "image": "mysql:latest",
                            "imagePullPolicy": "IfNotPresent",
                            "env": [
                                {
                                    "name": "MYSQL_ROOT_PASSWORD",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": "mysql-secret",
                                            "key": "mysql-root-password",
                                        }
                                    },
                                },
                                {"name": "MYSQL_DATABASE", "value": "zenml"},
                                {
                                    "name": "MYSQL_USER",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": "mysql-secret",
                                            "key": "mysql-user",
                                        }
                                    },
                                },
                                {
                                    "name": "MYSQL_PASSWORD",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": "mysql-secret",
                                            "key": "mysql-password",
                                        }
                                    },
                                },
                            ],
                            "ports": [{"containerPort": 3306}],
                            "volumeMounts": [
                                {
                                    "name": "mysql-storage",
                                    "mountPath": "/var/lib/mysql",
                                }
                            ],
                            "resources": {
                                "requests": {"cpu": "10m", "memory": "128Mi"},
                                "limits": {"cpu": "100m", "memory": "512Mi"},
                            },
                            "readinessProbe": {
                                "exec": {
                                    "command": ["mysqladmin", "ping", "-h", "localhost"]
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5,
                            },
                        }
                    ],
                    "volumes": [
                        {
                            "name": "mysql-storage",
                            "persistentVolumeClaim": {
                                "claimName": pvc.metadata["name"]
                            },
                        }
                    ],
                },
            },
        },
        opts=pulumi.ResourceOptions(
            provider=provider, depends_on=depends_on + [pvc, mysql_secret]
        ),
    )

    # MySQL Service
    service = k8s.core.v1.Service(
        "mysql",
        metadata={
            "name": "mysql",
            "namespace": namespace,
            "labels": {"app.kubernetes.io/name": "mysql"},
        },
        spec={
            "type": "ClusterIP",
            "ports": [
                {
                    "name": "mysql",
                    "port": 3306,
                    "targetPort": 3306,
                    "protocol": "TCP",
                }
            ],
            "selector": {"app.kubernetes.io/name": "mysql"},
        },
        opts=pulumi.ResourceOptions(
            provider=provider, depends_on=depends_on + [deployment]
        ),
    )

    return service
