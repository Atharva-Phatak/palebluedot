import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from infrastructure.helper.secrets import generate_mysql_secret, create_k8s_mysql_secret
from infrastructure.helper.constants import InfrastructureConfig


def deploy_mysql(
    k8s_provider: k8s.Provider,
    namespace: str,
    cfg: InfrastructureConfig,
    depends_on: list = None,
):
    sql_user, sql_password = generate_mysql_secret(
        project_id=cfg.infiscal_project_id,
        environment_slug="dev",
    )
    k8s_secret = create_k8s_mysql_secret(
        namespace=namespace,
        project_id=cfg.infiscal_project_id,
        environment_slug="dev",
        k8s_provider=k8s_provider,
    )

    depends_on = depends_on + [k8s_secret] if depends_on else [k8s_secret]

    mysql_chart = Chart(
        "mysql-chart",
        ChartOpts(
            chart="mysql",
            version="14.0.2",
            namespace=namespace,
            fetch_opts=FetchOpts(
                repo="https://charts.bitnami.com/bitnami",
            ),
            values={
                "global": {
                    "security": {
                        "allowInsecureImages": True  # Allow non-standard images
                    }
                },
                "image": {"repository": "bitnamilegacy/mysql"},
                "auth": {
                    "createDatabase": True,
                    "username": sql_user,
                    "existingSecret": "mysql-secret",
                    "usePasswordFiles": True,
                    "database": "zenml",
                },
                "primary": {
                    "persistence": {
                        "enabled": True,
                        "size": "8Gi",
                        "storageClass": "standard",  # Minikube default
                        # existingClaim: Not used anymore
                    },
                    "resources": {
                        "limits": {"cpu": "200m", "memory": "2Gi"},
                        "requests": {"cpu": "80m", "memory": "512Mi"},
                    },
                    "readinessProbe": {
                        "enabled": True,
                        "initialDelaySeconds": 5,
                        "periodSeconds": 5,
                    },
                },
                "service": {
                    "type": "ClusterIP",
                    "port": 3306,
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on if depends_on else [],
        ),
    )
    pulumi.export("sql_chart", mysql_chart.ready)
    return mysql_chart
