import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes.core.v1 import Namespace
from components.secret_manager.utils import get_infiscal_sdk


def get_postgres_secret(
    access_key_identifier: str, project_id: str, environment_slug: str
):
    """Retrieve the Postgres password from the secret manager."""
    client = get_infiscal_sdk()
    postgres_password = client.secrets.get_secret_by_name(
        secret_name=access_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
        secret_path="/",
    )
    return postgres_password.secretValue


def deploy_postgres(
    k8s_provider: k8s.Provider,
    namespace: Namespace,
    depends_on: list = None,
):
    postgres_chart = Chart(
        "metaflow-postgres",
        ChartOpts(
            chart="postgresql",
            version="12.1.7",
            fetch_opts=FetchOpts(repo="https://charts.bitnami.com/bitnami"),
            namespace=namespace.metadata["name"],
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
