import pulumi
import pulumi_kubernetes as k8s


def deploy_nvidia_gpu_operator(
    provider: k8s.Provider, namespace: k8s.core.v1.Namespace, depends_on: list = None
):
    nvidia_gpu_operator = k8s.helm.v3.Chart(
        "nvidia-gpu-operator",
        k8s.helm.v3.ChartOpts(
            chart="gpu-operator",
            version="v25.3.0",  # Make sure to check for latest compatible version
            fetch_opts=k8s.helm.v3.FetchOpts(repo="https://helm.ngc.nvidia.com/nvidia"),
            namespace=namespace.metadata["name"],
            values={
                "operator": {
                    "defaultRuntime": "docker"  # or "docker", depending on your setup
                },
                "driver": {"enabled": False},
                "toolkit": {
                    "enabled": False,
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=depends_on,
        ),
    )
    return nvidia_gpu_operator
