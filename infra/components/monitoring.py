import pulumi
import pulumi_kubernetes as k8s


def deploy_prometheus(
    depends_on: list, provider: k8s.Provider, namespace: k8s.core.v1.Namespace
):
    prometheus = k8s.helm.v3.Chart(
        "prometheus",
        k8s.helm.v3.ChartOpts(
            chart="prometheus",
            version="27.5.1",  # Update to latest stable version if needed
            fetch_opts=k8s.helm.v3.FetchOpts(
                repo="https://prometheus-community.github.io/helm-charts"
            ),
            namespace=namespace.metadata["name"],
            values={
                "server": {
                    "service": {"type": "ClusterIP"},
                    "resources": {
                        "requests": {
                            "cpu": "100m",
                            "memory": "128Mi",
                        },
                        "limits": {
                            "cpu": "250m",
                            "memory": "256Mi",
                        },
                    },
                }
            },
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )
    return prometheus


def deploy_grafana(
    depends_on: list,
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    admin_user: str = "admin",
    admin_password: str = "admin",
):
    """Deploys Grafana using Helm."""
    return k8s.helm.v3.Chart(
        "grafana",
        k8s.helm.v3.ChartOpts(
            chart="grafana",
            version="8.10.3",  # Update to latest stable version if needed
            fetch_opts=k8s.helm.v3.FetchOpts(
                repo="https://grafana.github.io/helm-charts"
            ),
            namespace=namespace.metadata["name"],
            values={
                "service": {"type": "ClusterIP"},
                "adminUser": admin_user,
                "adminPassword": admin_password,
                "resources": {
                    "requests": {
                        "cpu": "50m",
                        "memory": "64Mi",
                    },
                    "limits": {
                        "cpu": "200m",
                        "memory": "128Mi",
                    },
                },
            },
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )


def deploy_headlamp(
    depends_on: list,
    namespace: k8s.core.v1.Namespace,
    provider: k8s.Provider,
):
    headlamp = k8s.helm.v3.Chart(
        "headlamp",
        k8s.helm.v3.ChartOpts(
            chart="headlamp",
            version="0.29.1",  # Replace with the latest version
            fetch_opts=k8s.helm.v3.FetchOpts(
                repo="https://headlamp-k8s.github.io/headlamp"
            ),
            namespace=namespace.metadata["name"],
            values={
                "resources": {  # Minimal resource allocation
                    "requests": {
                        "cpu": "50m",
                        "memory": "64Mi",
                    },
                    "limits": {
                        "cpu": "100m",
                        "memory": "128Mi",
                    },
                },
            },
        ),
        opts=pulumi.ResourceOptions(depends_on=depends_on, provider=provider),
    )
