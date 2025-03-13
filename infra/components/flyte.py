import pulumi
import pulumi_kubernetes as k8s


def deploy_flyte(
    namespace: k8s.core.v1.Namespace, provider: k8s.Provider = None, depends_on=None
):
    # Deploy Flyte using the Helm Chart
    flyte_helm_chart = k8s.helm.v3.Chart(
        "flyte",
        k8s.helm.v3.ChartOpts(
            chart="flyte-core",  # Use "flyte-binary" if you want a single-binary deployment
            version="1.15.0",  # Set the correct Flyte version
            fetch_opts=k8s.helm.v3.FetchOpts(
                repo="https://flyteorg.github.io/flyte"  # Flyte Helm repo
            ),
            namespace=namespace.metadata["name"],
            values={
                "serviceAccount": {"create": True},
                "minio": {
                    "enabled": False
                },  # Disable MinIO if you're using an external MinIO
                "storage": {
                    "type": "s3",
                    "metadataContainer": "flyte-bucket",
                    "connection": {
                        "endpoint": "http://fsml-minio.info",  # Use your MinIO ingress
                        "region": "us-east-1",
                        "accessKey": "minio",
                        "secretKey": "minio123",
                    },
                },
                "database": {
                    "host": "postgres.flyte.svc.cluster.local",
                    "port": 5432,
                    "user": "flyte",
                    "password": "flytepassword",
                    "dbname": "flyte",
                },
                "config": {
                    "domain": "fsml.flyte.info",
                    "admin": {
                        "endpoint": "http://flyte-admin.flyte.svc.cluster.local:8088",
                    },
                },
            },
        ),
        opts=pulumi.ResourceOptions(depends_on=depends_on, provider=provider),
    )
    pulumi.export("flyte_ui", "http://flyte.example.com")
    pulumi.export("flyte_admin", "http://flyte-admin.flyte.svc.cluster.local:8088")
    return flyte_helm_chart
