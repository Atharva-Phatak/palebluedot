import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.helm.v3 import Chart, LocalChartOpts
from infrastructure.helper.secrets import get_infiscal_sdk

import os
import subprocess
from pathlib import Path


def get_argilla_secrets(
    access_key_identifier: str,
    secret_identifier: str,
    api_key_identifier: str,
    project_id: str,
    environment_slug: str = "dev",
):
    client = get_infiscal_sdk()
    argilla_username = client.secrets.get_secret_by_name(
        secret_name=access_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
        secret_path="/",
    )
    argilla_password = client.secrets.get_secret_by_name(
        secret_name=secret_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
        secret_path="/",
    )
    argilla_api_key = client.secrets.get_secret_by_name(
        secret_name=api_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
        secret_path="/",
    )
    return (
        argilla_username.secretValue,
        argilla_password.secretValue,
        argilla_api_key.secretValue,
    )


def get_argilla_chart_path(version: str = "v2.8.0") -> Path:
    """
    Downloads the Argilla Helm chart for the given release version if not already present.
    Returns the path to the chart directory.
    """
    # Clean version string (remove 'v' prefix if present)
    clean_version = version.lstrip("v")
    chart_path = Path(f"./charts/argilla-chart-{version}")

    if not chart_path.exists():
        print(f"📥 Downloading Argilla {version} chart...")
        tmp_dir = Path("./charts/tmp")
        archive = tmp_dir / f"argilla-{version}.zip"
        extracted = tmp_dir / f"argilla-{clean_version}"

        # Create directories
        os.makedirs(tmp_dir, exist_ok=True)
        os.makedirs(chart_path.parent, exist_ok=True)

        try:
            # Step 1: Download zip from GitHub release
            subprocess.run(
                [
                    "curl",
                    "-L",
                    "-o",
                    str(archive),
                    f"https://github.com/argilla-io/argilla/archive/refs/tags/{version}.zip",
                ],
                check=True,
            )

            # Step 2: Extract
            subprocess.run(
                ["unzip", "-q", str(archive), "-d", str(tmp_dir)], check=True
            )

            # Step 3: Check if the chart path exists and move it
            chart_src = extracted / "examples/deployments/k8s/argilla-chart"

            if not chart_src.exists():
                # Fallback: try to find the chart in different possible locations
                possible_paths = [
                    extracted / "examples/deployments/k8s/argilla-chart",
                    extracted / "deployments/k8s/argilla-chart",
                    extracted / "k8s/argilla-chart",
                    extracted / "helm/argilla-chart",
                ]

                chart_src = None
                for path in possible_paths:
                    if path.exists():
                        chart_src = path
                        break

                if chart_src is None:
                    raise FileNotFoundError(
                        f"Could not find argilla-chart in any expected location within {extracted}. "
                        f"Please check the repository structure for version {version}."
                    )

            # Copy the chart to the final location
            subprocess.run(["cp", "-r", str(chart_src), str(chart_path)], check=True)

            # Step 4: Cleanup
            subprocess.run(["rm", "-rf", str(tmp_dir)], check=True)

            print(
                f"✅ Successfully downloaded and extracted Argilla chart to {chart_path}"
            )

        except subprocess.CalledProcessError as e:
            print(f"❌ Error downloading or extracting chart: {e}")
            # Cleanup on error
            if tmp_dir.exists():
                subprocess.run(["rm", "-rf", str(tmp_dir)], check=False)
            raise

    pulumi.log.info(f"Argilla chart path: {chart_path.resolve()}")
    return chart_path.resolve()


def deploy_argilla(
    mount_path: str,
    k8s_provider: k8s.Provider,
    namespace: Namespace,
    argilla_access_key_identifier: str,
    argilla_secret_key_identifier: str,
    argilla_api_key_identifier: str,
    project_id: str,
    environment_slug: str = "dev",
    depends_on: list = None,
):
    chart_path = get_argilla_chart_path()

    argilla_access_key, argilla_secret_key, argilla_api_key = get_argilla_secrets(
        access_key_identifier=argilla_access_key_identifier,
        secret_identifier=argilla_secret_key_identifier,
        api_key_identifier=argilla_api_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
    )

    # Deploy Argilla Helm chart
    argilla_chart = Chart(
        "argilla-server",
        LocalChartOpts(
            namespace=namespace.metadata["name"],
            path=str(chart_path),
            values={
                "argilla": {
                    "authSecretKey": "argilla-auth-secret",
                    "auth": {
                        "username": argilla_access_key,
                        "password": argilla_secret_key,
                        "apiKey": argilla_api_key,
                    },
                    "persistence": {"mountPath": mount_path, "size": "10Gi"},
                    "ingress": {
                        "host": "argilla.palebluedot.io",
                        "annotations": {
                            "nginx.ingress.kubernetes.io/rewrite-target": "/",
                            "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                            "nginx.ingress.kubernetes.io/proxy-body-size": "64m",
                            "nginx.ingress.kubernetes.io/proxy-connect-timeout": "300",
                            "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                            "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
                        },
                    },
                    "hpa": {
                        "enabled": False,
                        "maxReplicas": 2,
                    },
                    "elasticsearch": {
                        "sslVerify": False,
                    },
                    "redis": {
                        "enabled": False,
                    },
                    "externalRedis": {
                        "enabled": True,
                        "url": "redis://redis-master:6379/0",
                        "is_redis_cluster": False,
                    },
                    "worker": {"numWorkers": 1},
                }
            },
        ),
        opts=pulumi.ResourceOptions(
            depends_on=depends_on,
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="15m"),
        ),
    )
    pulumi.export("argilla_ready", argilla_chart.ready)
    # if chart_path.exists():
    #    subprocess.run(["rm", "-rf", str(chart_path)], check=True)
    return argilla_chart
