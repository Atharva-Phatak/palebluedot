from applications.argilla.deploy_argilla import deploy_argilla
from applications.argilla.deploy_elasticsearch import deploy_elasticsearch
from applications.argilla.deploy_redis import deploy_redis
from applications.k8s.namespace import create_namespace
import pulumi_kubernetes as k8s


def deploy_argilla_component(
    cfg,
    argilla_access_key_identifier: str,
    argilla_secret_key_identifier: str,
    argilla_api_key_identifier: str,
    k8s_provider: k8s.Provider,
    depends_on: list,
):
    # Create Argilla namespace
    argilla_namespace = create_namespace(
        provider=k8s_provider, namespace="argilla", depends_on=depends_on
    )

    # Deploy Elasticsearch
    elasticsearch_chart = deploy_elasticsearch(
        k8s_provider=k8s_provider,
        namespace=argilla_namespace,
        depends_on=depends_on + [argilla_namespace],
    )
    redis_chart = deploy_redis(
        k8s_provider=k8s_provider,
        namespace=argilla_namespace,
        mount_path=cfg.redis_mount_path,
        replica_mount_path=cfg.redis_replica_mount_path,
        depends_on=depends_on + [elasticsearch_chart],
    )
    # Deploy Argilla
    argilla_chart = deploy_argilla(
        k8s_provider=k8s_provider,
        namespace=argilla_namespace,
        depends_on=depends_on + [elasticsearch_chart, redis_chart],
        mount_path=cfg.argilla_mount_path,
        argilla_access_key_identifier=argilla_access_key_identifier,
        argilla_secret_identifier=argilla_secret_key_identifier,
        argilla_api_key_identifier=argilla_api_key_identifier,
        project_id=cfg.infiscal_project_id,
        environment_slug=cfg.environment_slug,
    )

    return argilla_chart
