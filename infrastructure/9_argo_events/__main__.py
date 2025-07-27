from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config
from infrastructure.components.argo.argo_events.deploy_argo_events import (
    deploy_argo_events,
)
from infrastructure.components.argo.argo_events.event_sources.metaflow import (
    deploy_metaflow_event_source,
)
from infrastructure.components.argo.argo_events.event_sources.minio import (
    deploy_minio_event_source,
)
from infrastructure.components.argo.argo_events.sensors.minio_sensor import (
    deploy_minio_sensor,
)

from infrastructure.helper.secrets import create_aws_secret
import pulumi
from pulumi import StackReference


provider = get_k8s_provider()
config = load_config()
pconfig = pulumi.Config()
namespace_name = pconfig.require("metaflow_namespace")
metaflow_stack = StackReference("organization/metaflow/6_orchestrator")


metaflow_config = metaflow_stack.get_output("metaflow_config")

aws_secret = create_aws_secret(
    provider=provider,
    namespace=namespace_name,
    project_id=config.infiscal_project_id,
)
argo_events, argo_metaflow_config = deploy_argo_events(
    k8s_provider=provider,
    depends_on=[aws_secret],
    namespace=namespace_name,
)
_ = deploy_metaflow_event_source(
    provider=provider,
    namespace=namespace_name,
    depends_on=[argo_events, aws_secret],
)
_ = deploy_minio_event_source(
    provider=provider,
    aws_secret=aws_secret,
    namespace=namespace_name,
    depends_on=[aws_secret, argo_events],
)
_ = deploy_minio_sensor(
    namespace=namespace_name,
    provider=provider,
    depends_on=[aws_secret, argo_events],
)
full_config = metaflow_config.apply(lambda config: {**config, **argo_metaflow_config})
pulumi.export("metaflow_config", full_config)
