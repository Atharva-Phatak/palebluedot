import pulumi_kubernetes as k8s
import pulumi


def create_namespace(provider: k8s.Provider, namespace: str, depends_on: list = None):
    # Create the flyte namespace
    namespace = k8s.core.v1.Namespace(
        namespace,
        metadata={"name": namespace},
        opts=pulumi.ResourceOptions(provider=provider, depends_on=depends_on),
    )
    return namespace
