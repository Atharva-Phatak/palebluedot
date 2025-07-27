import pulumi
from infrastructure.helper.secrets import create_postgres_secret
from infrastructure.helper.config import load_config
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.components.postgres.deploy_postgres import deploy_postgres

config = load_config()
pconfig = pulumi.Config()
namespace_name = pconfig.require("metaflow_namespace")


provider = get_k8s_provider()

postgres_secret = create_postgres_secret(
    namespace=namespace_name,
    project_id=config.infiscal_project_id,
    environment_slug="dev",
    access_key_identifier="postgres_password",
    k8s_provider=provider,
)
postgres_resource = deploy_postgres(
    k8s_provider=provider,
    namespace=namespace_name,
    depends_on=[postgres_secret],
)
