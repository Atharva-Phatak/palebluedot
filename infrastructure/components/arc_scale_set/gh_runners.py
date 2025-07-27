import os

import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts
from pulumi_kubernetes.core.v1 import Namespace


def deploy_arc_controller(
    depends_on: list, namespace: Namespace, k8s_provider: k8s.Provider
):
    arc_controller = Chart(
        "arc",
        ChartOpts(
            chart="oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller",
            namespace=namespace.metadata["name"],
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


def deploy_arc_scale_set(
    depends_on: list[str],
    namespace: Namespace,
    k8s_provider: k8s.Provider,
    github_secret: k8s.core.v1.Secret,
) -> Chart:
    github_url = os.environ.get("GITHUB_URL")

    arc_runner_scale_set = Chart(
        "pbd-runner-scale-set",
        ChartOpts(
            chart="oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set",
            namespace=namespace.metadata["name"],
            values={
                "githubConfigUrl": github_url,
                "githubConfigSecret": github_secret.metadata["name"],
                "containerMode": {"type": "dind"},  # Docker-in-Docker support
                "controllerServiceAccount": {
                    "namespace": "arc-ns",
                    "instance": "arc",
                    "name": "arc-gha-rs-controller",
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            depends_on=depends_on,
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="20m"),
        ),
    )
    pulumi.export("arc_scale_set_status", arc_runner_scale_set.ready)
    return arc_runner_scale_set
