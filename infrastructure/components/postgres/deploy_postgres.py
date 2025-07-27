import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts


def deploy_postgres(
    k8s_provider: k8s.Provider,
    namespace: str,
    depends_on: list = None,
):
    postgres_chart = Chart(
        "metaflow-postgres",
        ChartOpts(
            chart="postgresql",
            version="12.1.7",
            fetch_opts=FetchOpts(repo="https://charts.bitnami.com/bitnami"),
            namespace=namespace,
            values={
                "auth": {
                    "existingSecret": "metaflow-db-secret",
                    "username": "metaflow",
                    "database": "metaflow",
                    "secretKeys": {"userPasswordKey": "postgres-password"},
                },
                "primary": {"persistence": {"enabled": True, "size": "10Gi"}},
                "resources": {
                    "requests": {"cpu": "80m", "memory": "512Mi"},
                    "limits": {"cpu": "200m", "memory": "2Gi"},
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on if depends_on else [],
        ),
    )
    pulumi.export("postgres_chart", postgres_chart.ready)
    return postgres_chart
