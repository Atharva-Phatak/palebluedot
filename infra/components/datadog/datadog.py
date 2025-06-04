import os

import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts


def deploy_datadog(depends_on: list, k8s_provider: k8s.Provider, namespace: str):
    datadog_api_key = os.environ.get("DATADOG_API_KEY")
    datadog_app_key = os.environ.get("DATADOG_APP_KEY")
    datadog_chart = Chart(
        "prometheus",
        ChartOpts(
            chart="datadog",
            version="3.69.0",  # Latest stable version
            namespace=namespace,
            fetch_opts=FetchOpts(repo="https://helm.datadoghq.com"),
            values={
                "datadog": {
                    "apiKey": str(datadog_api_key),
                    "appKey": str(datadog_app_key),
                    "site": "us5.datadoghq.com",
                    "kubelet": {"tlsVerify": False},
                    "logs": {
                        "enabled": True,
                        "containerCollectAll": True,
                        "containerCollectUsingFiles": True,
                    },
                    "apm": {
                        "enabled": True,
                        "portEnabled": True,
                        "socketEnabled": True,
                        "instrumentation": {
                            "enabled": True,
                            "enabledNamespaces": ["default"],
                        },
                    },
                    "processAgent": {"enabled": True, "processCollection": True},
                }
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on,
        ),
    )
    pulumi.export("datadog_status", datadog_chart.ready)
