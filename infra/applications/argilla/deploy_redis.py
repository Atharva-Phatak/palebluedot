import pulumi
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
import pulumi_kubernetes as k8s


def deploy_redis(
    k8s_provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    mount_path: str,
    replica_mount_path: str = None,
    depends_on: list = None,
):
    redis_chart = Chart(
        "redis",
        ChartOpts(
            chart="redis",
            version="17.11.4",  # or the latest compatible version
            fetch_opts=FetchOpts(
                repo="https://charts.bitnami.com/bitnami",
            ),
            namespace=namespace.metadata["name"],
            values={
                "fullnameOverride": "argilla-server-redis",
                "architecture": "standalone",
                "auth": {"enabled": False},  # no password for dev simplicity
                "master": {
                    "persistence": {
                        "enabled": True,
                        "path": mount_path,
                        "size": "4Gi",
                        "accessModes": ["ReadWriteOnce"],
                    },
                    "resources": {
                        "requests": {
                            "cpu": "100m",
                            "memory": "128Mi",
                        },
                        "limits": {
                            "cpu": "200m",
                            "memory": "256Mi",
                        },
                    },
                },
                "replica": {
                    "replicaCount": 1,
                    "persistence": {
                        "enabled": True,
                        "path": replica_mount_path,
                        "size": "4Gi",
                        "accessModes": ["ReadWriteOnce"],
                    },
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=depends_on,
            custom_timeouts=pulumi.CustomTimeouts(create="20m"),
        ),
    )

    # pulumi.export("redis_service", redis_chart.get_resource("v1/Service", "redis"))
    return redis_chart
