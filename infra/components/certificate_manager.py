from applications.k8s.namespace import create_namespace
from applications.certificate_managers.deploy_certificate_managers import (
    deploy_cert_manager,
)
import pulumi_kubernetes as k8s


def deploy_certificate_manager(
    depends_on: list,
    provider: k8s.Provider,
):
    certificate_namespace = create_namespace(
        provider=provider,
        namespace="cert-manager",
        depends_on=depends_on,
    )
    return deploy_cert_manager(
        k8s_provider=provider,
        namespace=certificate_namespace,
        depends_on=depends_on + [certificate_namespace],
    )
