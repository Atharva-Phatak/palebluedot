import pulumi_kubernetes as k8s
import pulumi
import os
import subprocess
from pulumi_kubernetes.helm.v3 import Release, LocalChartOpts, ReleaseArgs


def download_zenml_helm_chart():
    # Download the chart directly from GitHub
    chart_version = "0.75.0"  # Replace with your desired version
    chart_url = (
        f"https://github.com/zenml-io/zenml/archive/refs/tags/{chart_version}.zip"
    )
    download_path = f"/tmp/zenml-{chart_version}.zip"
    extract_path = f"/tmp/zenml-{chart_version}"
    chart_path = f"{extract_path}/zenml-{chart_version}/helm"

    # Download and extract if not already done
    if not os.path.exists(chart_path):
        subprocess.run(["curl", "-L", chart_url, "-o", download_path], check=True)
        subprocess.run(["unzip", "-q", download_path, "-d", extract_path], check=True)

    return chart_path


def deploy_zenml(
    depends_on: list = None,
    k8s_provider: k8s.Provider = None,
    namespace: str = "zenml-namespace",
) -> k8s.core.v1.Service:
    chart_path = download_zenml_helm_chart()
    helm_chart = k8s.helm.v3.Chart(
        "zenml",
        config=LocalChartOpts(
            path=chart_path,
            values={
                "zenml": {
                    "analyticsOptIn": False,
                    "auth": {"authType": "NO_AUTH"},
                    "database": {
                        # MySQL connection URL without password
                        "url": f"mysql://zenml:zenml@mysql.{namespace}.svc.cluster.local:3306/zenml",
                        # Reference to the Kubernetes secret for password
                        "passwordSecretRef": {
                            "name": "mysql-secret",
                            "key": "mysql-password",
                        },
                    },
                    "secretStore": {"enabled": False},
                    "ingress": {
                        "enabled": True,
                        "host": "palebluedot-zenml.io",
                        "annotations": {
                            "nginx.ingress.kubernetes.io/rewrite-target": "/",
                            "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                            "nginx.ingress.kubernetes.io/proxy-body-size": "64m",
                            "nginx.ingress.kubernetes.io/proxy-connect-timeout": "300",
                            "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                            "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
                        },
                    },
                }
            },
            namespace=namespace,
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on,
        ),
    )
    pulumi.export("zenml_service", helm_chart.ready)
