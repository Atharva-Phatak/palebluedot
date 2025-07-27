import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts


def deploy_grafana(provider: k8s.Provider, depends_on: list, namespace: str):
    grafana_chart = Chart(
        "grafana",
        ChartOpts(
            chart="grafana",
            version="9.2.7",  # Check latest
            fetch_opts=FetchOpts(
                repo="https://grafana.github.io/helm-charts",
            ),
            namespace=namespace,
            values={
                "resources": {
                    "requests": {
                        "cpu": "100m",
                        "memory": "256Mi",
                    },
                    "limits": {
                        "cpu": "300m",
                        "memory": "512Mi",
                    },
                },
                "adminPassword": "admin",  # CHANGE IN PRODUCTION
                "service": {"type": "ClusterIP"},
                "datasources": {
                    "datasources.yaml": {
                        "apiVersion": 1,
                        "datasources": [
                            {
                                "name": "Prometheus",
                                "type": "prometheus",
                                "url": "http://prometheus-server.monitoring.svc.cluster.local",
                                "access": "proxy",
                                "isDefault": True,
                            }
                        ],
                    }
                },
                "ingress": {
                    "enabled": True,
                    "annotations": {
                        "nginx.ingress.kubernetes.io/rewrite-target": "/",
                        "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                        "nginx.ingress.kubernetes.io/proxy-body-size": "64m",
                        "nginx.ingress.kubernetes.io/proxy-connect-timeout": "300",
                        "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                        "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
                    },
                    "hosts": ["grafana-palebluedot.io"],
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on,
        ),
    )
    pulumi.export("grafana_chart", grafana_chart.ready)
    return grafana_chart
