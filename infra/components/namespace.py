import pulumi_kubernetes as k8s
import pulumi


def create_flyte_namespace(provider: k8s.Provider, depends_on: list = None):
    # Create the flyte namespace
    namespace = k8s.core.v1.Namespace(
        "flyte-namespace",
        metadata={"name": "flyte"},
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )
    return namespace
