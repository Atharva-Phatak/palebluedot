from infrastructure.components.argilla.deploy_argilla import deploy_argilla
from infrastructure.components.argilla.deploy_elasticsearch import deploy_elasticsearch
from infrastructure.components.argilla.deploy_redis import deploy_redis
from infrastructure.helper.namespace import create_namespace
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config

provider = get_k8s_provider()
cfg = load_config()
# Create Argilla namespace
argilla_namespace = create_namespace(provider=provider, namespace="argilla")

# Deploy Elasticsearch
elasticsearch_chart = deploy_elasticsearch(
    k8s_provider=provider,
    namespace=argilla_namespace,
    depends_on=[argilla_namespace],
)
redis_chart = deploy_redis(
    k8s_provider=provider,
    namespace=argilla_namespace,
    mount_path=cfg.redis_mount_path,
    replica_mount_path=cfg.redis_replica_mount_path,
    depends_on=[elasticsearch_chart],
)
# Deploy Argilla
argilla_chart = deploy_argilla(
    k8s_provider=provider,
    namespace=argilla_namespace,
    depends_on=[elasticsearch_chart, redis_chart],
    mount_path=cfg.argilla_mount_path,
    argilla_access_key_identifier="argilla_username",
    argilla_secret_key_identifier="argilla_password",
    argilla_api_key_identifier="argilla_api_key",
    project_id=cfg.infiscal_project_id,
    environment_slug="dev",
)
