import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.apiextensions import CustomResource


def deploy_cert_manager(
    namespace: Namespace, k8s_provider: k8s.Provider, depends_on: list = None
):
    cert_manager = Chart(
        "cert-manager",
        ChartOpts(
            chart="cert-manager",
            version="v1.18.0",
            fetch_opts=FetchOpts(repo="https://charts.jetstack.io"),
            namespace=namespace.metadata["name"],
            values={"installCRDs": True},
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on or [],  # Handle None case
        ),
    )

    cluster_issuer = CustomResource(
        "letsencrypt-cluster-issuer",
        api_version="cert-manager.io/v1",
        kind="ClusterIssuer",
        metadata={"name": "letsencrypt-staging"},
        spec={
            "acme": {
                "email": "athp456@gmail.com",
                "server": "https://acme-staging-v02.api.letsencrypt.org/directory",
                "privateKeySecretRef": {"name": "letsencrypt-staging-key"},
                "solvers": [
                    {
                        "http01": {
                            "ingress": {
                                "class": "nginx",
                                "pathType": "Prefix",  # Add this line
                            }
                        }
                    }
                ],
            }
        },
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on + [cert_manager],  # Handle None case
        ),
    )
    pulumi.export("cert_manager_status", cert_manager.ready)
    return cert_manager, cluster_issuer
