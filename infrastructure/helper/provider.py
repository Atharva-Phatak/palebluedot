import pulumi_kubernetes as k8s
import pulumi


def get_k8s_provider(depends_on: list = None):
    provider = k8s.Provider(
        "minikube-provider",
        kubeconfig="~/.kube/config",  # Ensure this is the correct path to your kubeconfig
        context="minikube",  # Use the 'minikube' context here
        opts=pulumi.ResourceOptions(depends_on=depends_on),
    )
    return provider
