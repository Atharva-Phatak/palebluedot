from components.gh_runners.arc_controller import deploy_arc_controller
from components.gh_runners.arc_scale_set import deploy_arc_scale_set
from components.grafana.deploy_grafana import deploy_grafana
from components.k8s.minikube import start_minikube
from components.k8s.namespace import create_namespace
from components.k8s.provider import get_k8s_provider
from components.metaflow.deploy_metaflow import deploy_metaflow, create_metaflow_config
from components.minio.buckets import deploy_minio_buckets
from components.minio.minio import deploy_minio
from components.persistent_claims.pv import deploy_persistent_volume_claims

# from components.sql.mysql import deploy_mysql
# from components.zenml.zenml import deploy_zenml
from components.postgres.deploy_postgres import deploy_postgres
from components.prometheus.deploy_prometheus import deploy_prometheus
from components.secret_manager.secrets import (
    create_aws_secret,
    create_gh_secret,
    create_postgres_secret,
    create_slack_secret,
)
from omegaconf import OmegaConf
from components.argo.argo_workflows.deploy_argo_workflows import deploy_argo_workflows
from components.argo.argo_events.deploy_argo_events import deploy_argo_events
from components.argo.argo_events.event_sources.metaflow import (
    deploy_metaflow_event_source,
)
from components.argo.argo_events.event_sources.minio import deploy_minio_event_source
from components.argo.argo_events.sensors.minio_sensor import deploy_minio_sensor
from components.webhooks.metaflow_webhook import deploy_metaflow_webhook


def load_config():
    cfg = OmegaConf.load("configs/config.yaml")
    return cfg


# load config and constants in the yaml
cfg = load_config()
# Ensure Minikube starts before deploying resources
minikube_start = start_minikube(
    n_cpus=cfg.minikube_cpus,
    memory=cfg.minikube_memory,
    addons=cfg.minikube_addons,
    gpus=cfg.minikube_gpus,
    disk_size=cfg.minikube_disk_size,
    models_mount_path=cfg.model_storage_path,
)

k8s_provider = get_k8s_provider(depends_on=[minikube_start])
monitoring_namespace = create_namespace(
    provider=k8s_provider, namespace="monitoring", depends_on=[minikube_start]
)
arc_namespace = create_namespace(
    provider=k8s_provider, namespace="arc-ns", depends_on=[minikube_start]
)
metaflow_namespace = create_namespace(
    provider=k8s_provider, namespace="metaflow", depends_on=[minikube_start]
)
aws_secret = create_aws_secret(
    provider=k8s_provider,
    namespace="metaflow",
    depends_on=[minikube_start, metaflow_namespace],
    infiscal_project_id=cfg.infiscal_project_id,
)
postgres_secret = create_postgres_secret(
    namespace="metaflow",
    project_id=cfg.infiscal_project_id,
    environment_slug="dev",
    access_key_identifier="postgres_password",
    k8s_provider=k8s_provider,
    depends_on=[minikube_start, metaflow_namespace],
)
gh_secret = create_gh_secret(
    k8s_provider=k8s_provider,
    depends_on=[arc_namespace, minikube_start],
    namespace="arc-ns",
)
slack_secret = create_slack_secret(
    namespace="metaflow",
    depends_on=[metaflow_namespace, minikube_start],
    k8s_provider=k8s_provider,
)
# Deploy postgres
postgres_resource = deploy_postgres(
    k8s_provider=k8s_provider,
    namespace=metaflow_namespace,
    depends_on=[minikube_start, metaflow_namespace, postgres_secret],
)


# Deploy Persistent Volume Claims
minio_pv_claim = deploy_persistent_volume_claims(
    namespace=metaflow_namespace,
    provider=k8s_provider,
    pv_name=cfg.pv_name,
    pvc_name=cfg.pvc_name,
    storage_capacity=cfg.mk_storage_capacity,
    storage_path=cfg.storage_path,
    depends_on=[minikube_start, metaflow_namespace],
)
model_pv_claims = deploy_persistent_volume_claims(
    namespace=metaflow_namespace,
    provider=k8s_provider,
    pv_name=cfg.model_pv_name,
    pvc_name=cfg.model_pvc_name,
    storage_capacity=cfg.model_storage_capacity,
    storage_path=cfg.model_storage_path,
    depends_on=[minikube_start, metaflow_namespace],
)

# Deploy MinIO
minio_chart = deploy_minio(
    provider=k8s_provider,
    namespace=metaflow_namespace,
    ingress_host=cfg.minio_ingress_host,
    deployment_name=cfg.minio_deployment_name,
    service_name=cfg.minio_service_name,
    pvc_name=minio_pv_claim.metadata["name"],
    depends_on=[metaflow_namespace, minio_pv_claim],
    access_key_identifier="minio_access_key",
    secret_key_identifier="minio_secret_key",
    project_id=cfg.infiscal_project_id,
    environment_slug="dev",
)
# Deploy MinIO buckets
deploy_minio_buckets(
    access_key_identifier="minio_access_key",
    secret_key_identifier="minio_secret_key",
    infiscal_project_id=cfg.infiscal_project_id,
    environment_slug="dev",
    depends_on=[
        minio_chart,
        minikube_start,
        postgres_resource,
        model_pv_claims,
        minio_pv_claim,
        metaflow_namespace,
    ],
    buckets=[cfg.data_bucket, cfg.zenml_bucket],
    ingress_host=cfg.minio_ingress_host,
)
# deploy metaflow
metaflow_chart, metaflow_config = deploy_metaflow(
    k8s_provider=k8s_provider,
    namespace=metaflow_namespace,
    infiscal_project_id=cfg.infiscal_project_id,
    environment_slug="dev",
    access_key_identifier="postgres_password",
    aws_access_key_identifier="minio_access_key",
    aws_secret_key_identifier="minio_secret_key",
    depends_on=[minikube_start, metaflow_namespace, postgres_resource, minio_chart],
)


# Deploy ARC Controller, deploy after zenml is deployed
arc_controller_resource = deploy_arc_controller(
    depends_on=[minikube_start, arc_namespace, metaflow_chart],
    namespace="arc-ns",
    k8s_provider=k8s_provider,
)
# Deploy ARC Scale Set
arc_scale_set_resource = deploy_arc_scale_set(
    depends_on=[
        minikube_start,
        arc_namespace,
        metaflow_chart,
        arc_controller_resource,
        gh_secret,
    ],
    namespace="arc-ns",
    k8s_provider=k8s_provider,
    github_secret=gh_secret,
)
# Deploy prometheus and grafana
prometheus_chart = deploy_prometheus(
    depends_on=[minikube_start, monitoring_namespace, metaflow_chart],
    provider=k8s_provider,
    namespace=monitoring_namespace,
)
# deploy_grafana(
grafana_chart = deploy_grafana(
    provider=k8s_provider,
    depends_on=[minikube_start, monitoring_namespace, prometheus_chart, metaflow_chart],
    namespace=monitoring_namespace,
)
# Deploy Argo Workflows and Events
argo_workflows_chart = deploy_argo_workflows(
    k8s_provider=k8s_provider,
    depends_on=[minikube_start, monitoring_namespace, metaflow_chart],
    namespace=metaflow_namespace,
)
argo_events, argo_metaflow_config = deploy_argo_events(
    k8s_provider=k8s_provider,
    depends_on=[
        minikube_start,
        monitoring_namespace,
        metaflow_chart,
        argo_workflows_chart,
    ],
    namespace=metaflow_namespace,
)
metaflow_event_source = deploy_metaflow_event_source(
    provider=k8s_provider,
    namespace=metaflow_namespace,
    depends_on=[argo_events, argo_workflows_chart, metaflow_chart, minikube_start],
)
minio_event_source = deploy_minio_event_source(
    provider=k8s_provider,
    aws_secret=aws_secret,
    namespace=metaflow_namespace,
    depends_on=[argo_events, argo_workflows_chart, metaflow_chart, minikube_start],
)
minio_sensor = deploy_minio_sensor(
    namespace=metaflow_namespace,
    provider=k8s_provider,
    depends_on=[
        minikube_start,
        metaflow_event_source,
        minio_event_source,
        argo_events,
        argo_workflows_chart,
        metaflow_chart,
    ],
)
metaflow_webhook_service = deploy_metaflow_webhook(
    namespace=metaflow_namespace,
    provider=k8s_provider,
    depends_on=[
        minikube_start,
        metaflow_event_source,
        minio_event_source,
        minio_sensor,
        argo_events,
        argo_workflows_chart,
        metaflow_chart,
        metaflow_namespace,
    ],
)
# Create the full Metaflow configuration
full_metaflow_config = metaflow_config | argo_metaflow_config
create_metaflow_config(
    config=full_metaflow_config,
    depends_on=[
        minikube_start,
        metaflow_chart,
        postgres_resource,
        minio_chart,
        model_pv_claims,
        minio_pv_claim,
        gh_secret,
        arc_controller_resource,
        arc_scale_set_resource,
        prometheus_chart,
        grafana_chart,
        argo_workflows_chart,
        argo_events,
    ],
)
