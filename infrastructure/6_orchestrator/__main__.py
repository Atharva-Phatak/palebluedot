import pulumi
from infrastructure.components.metaflow.deploy_metaflow import deploy_metaflow
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config


provider = get_k8s_provider()
pconfig = pulumi.Config()
namespace_name = pconfig.require("metaflow_namespace")
config = load_config()
metaflow_chart, metaflow_config = deploy_metaflow(
    k8s_provider=provider,
    namespace=namespace_name,
    infiscal_project_id=config.infiscal_project_id,
    environment_slug="dev",
    access_key_identifier="postgres_password",
    aws_access_key_identifier="minio_access_key",
    aws_secret_key_identifier="minio_secret_key",
)
pulumi.export("metaflow_config", metaflow_config)
