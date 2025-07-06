import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import Namespace
from applications.argo.argo_workflows.deploy_argo_workflows import deploy_argo_workflows
from applications.argo.argo_events.deploy_argo_events import deploy_argo_events
from applications.argo.argo_events.event_sources.metaflow import (
    deploy_metaflow_event_source,
)
from applications.argo.argo_events.event_sources.minio import deploy_minio_event_source
from applications.argo.argo_events.sensors.minio_sensor import deploy_minio_sensor
from applications.webhooks.metaflow_webhook import deploy_metaflow_webhook

from applications.secret_manager.secrets import create_aws_secret


def deploy_argo_components(
    cfg, k8s_provider: k8s.Provider, namespace: Namespace, depends_on: list = None
):
    aws_secret = create_aws_secret(
        provider=k8s_provider,
        namespace=namespace,
        depends_on=depends_on,
        infiscal_project_id=cfg.infiscal_project_id,
    )
    # Deploy Argo Workflows and Events
    argo_workflows_chart = deploy_argo_workflows(
        k8s_provider=k8s_provider,
        depends_on=depends_on,
        namespace=namespace,
    )
    argo_events, argo_metaflow_config = deploy_argo_events(
        k8s_provider=k8s_provider,
        depends_on=depends_on + [argo_workflows_chart],
        namespace=namespace,
    )
    _ = deploy_metaflow_event_source(
        provider=k8s_provider,
        namespace=namespace,
        depends_on=depends_on + [argo_events, argo_workflows_chart, aws_secret],
    )
    _ = deploy_minio_event_source(
        provider=k8s_provider,
        aws_secret=aws_secret,
        namespace=namespace,
        depends_on=depends_on + [argo_events, argo_workflows_chart, aws_secret],
    )
    _ = deploy_minio_sensor(
        namespace=namespace,
        provider=k8s_provider,
        depends_on=depends_on + [argo_events, argo_workflows_chart, aws_secret],
    )
    _ = deploy_metaflow_webhook(
        namespace=namespace,
        provider=k8s_provider,
        depends_on=depends_on + [argo_events, argo_workflows_chart, aws_secret],
    )
    return argo_metaflow_config
