from pulumi_kubernetes.core.v1 import Namespace
import pulumi_kubernetes as k8s
from applications.metaflow.deploy_metaflow import deploy_metaflow
from applications.k8s.namespace import create_namespace


def deploy_metaflow_namespace(k8s_provider: k8s.Provider, depends_on: list = None):
    metaflow_namespace = create_namespace(
        provider=k8s_provider, namespace="metaflow", depends_on=depends_on
    )
    return metaflow_namespace


def deploy_metaflow_component(
    k8s_provider: k8s.Provider, namespace: Namespace, cfg, depends_on: list = None
):
    # deploy metaflow
    metaflow_chart, metaflow_config = deploy_metaflow(
        k8s_provider=k8s_provider,
        namespace=namespace,
        infiscal_project_id=cfg.infiscal_project_id,
        environment_slug="dev",
        access_key_identifier="postgres_password",
        aws_access_key_identifier="minio_access_key",
        aws_secret_key_identifier="minio_secret_key",
        depends_on=depends_on,
    )
    return metaflow_chart, metaflow_config
