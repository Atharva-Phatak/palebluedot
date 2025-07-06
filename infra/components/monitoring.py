import pulumi_kubernetes as k8s
from applications.prometheus.deploy_prometheus import deploy_prometheus
from applications.grafana.deploy_grafana import deploy_grafana
from applications.k8s.namespace import create_namespace


def deploy_monitoring_components(
    k8s_provider: k8s.Provider, cfg, depends_on: list = None
):

    monitoring_namespace = create_namespace(
        provider=k8s_provider, namespace="monitoring", depends_on=depends_on
    )
    # Deploy prometheus and grafana
    prometheus_chart = deploy_prometheus(
        depends_on=depends_on + [monitoring_namespace],
        provider=k8s_provider,
        namespace=monitoring_namespace,
    )
    # deploy_grafana(
    grafana_chart = deploy_grafana(
        provider=k8s_provider,
        depends_on=depends_on + [monitoring_namespace],
        namespace=monitoring_namespace,
    )

    return prometheus_chart, grafana_chart
