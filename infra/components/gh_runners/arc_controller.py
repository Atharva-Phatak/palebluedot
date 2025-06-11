import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts


def deploy_arc_controller(depends_on: list, namespace: str, k8s_provider: k8s.Provider):
    arc_controller = Chart(
        "arc",
        ChartOpts(
            chart="oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller",
            namespace=namespace,
            # Note: Pulumi will handle dependency on namespace creation
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="20m"),
            depends_on=depends_on,
        ),
    )
    pulumi.export("arc_controller_status", arc_controller.ready)
    return arc_controller
