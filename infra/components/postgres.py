from applications.postgres.deploy_postgres import deploy_postgres
from pulumi_kubernetes.core.v1 import Namespace
import pulumi_kubernetes as k8s
from applications.secret_manager.secrets import create_postgres_secret


def deploy_postgres_component(
    cfg,
    k8s_provider: k8s.Provider,
    namespace: Namespace,
    depends_on: list,
):
    postgres_secret = create_postgres_secret(
        namespace=namespace,
        project_id=cfg.infiscal_project_id,
        environment_slug="dev",
        access_key_identifier="postgres_password",
        k8s_provider=k8s_provider,
        depends_on=depends_on,
    )
    # Deploy postgres
    postgres_resource = deploy_postgres(
        k8s_provider=k8s_provider,
        namespace=namespace,
        depends_on=depends_on + [postgres_secret],
    )
    return postgres_resource
