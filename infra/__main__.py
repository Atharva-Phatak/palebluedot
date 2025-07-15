from omegaconf import OmegaConf
from components.cluster import deploy_minikube_cluster
from components.minio import deploy_minio_component
from components.postgres import deploy_postgres_component
from components.arc_controller import deploy_arc_components
from components.metaflow import (
    deploy_metaflow_component,
    deploy_metaflow_namespace,
)
from components.monitoring import deploy_monitoring_components
from components.argo import deploy_argo_components
from components.configuration import deploy_metaflow_config_component
from components.slack import deploy_slack_secret
from components.annotator import deploy_argilla_component
from components.models_pvc import deploy_models_pvc
from applications.secret_manager.secrets import create_argilla_secret
from components.wehooks import deploy_metaflow_webhook_components


def load_config():
    cfg = OmegaConf.load("configs/config.yaml")
    return cfg


# load config and constants in the yaml
cfg = load_config()
# Ensure Minikube starts before deploying resources
provider, minikube_start = deploy_minikube_cluster(cfg)


# create metaflow namespace as most components depend on it

metaflow_namespace = deploy_metaflow_namespace(
    k8s_provider=provider,
    depends_on=[minikube_start],
)

# Create slack secret
slack_secret = deploy_slack_secret(
    k8s_provider=provider,
    namespace=metaflow_namespace,
    depends_on=[minikube_start, metaflow_namespace],
)

# Deploy models PVC
deploy_models_pvc(
    cfg=cfg,
    namespace=metaflow_namespace,
    k8s_provider=provider,
    depends_on=[minikube_start, metaflow_namespace],
)

create_argilla_secret(
    namespace=metaflow_namespace,
    argilla_access_key_identifier="argilla_username",
    argilla_secret_key_identifier="argilla_password",
    argilla_api_key_identifier="argilla_api_key",
    k8s_provider=provider,
    project_id=cfg.infiscal_project_id,
    depends_on=[minikube_start, metaflow_namespace],
)

# Deploy minio with buckets
minio_chart = deploy_minio_component(
    cfg=cfg,
    k8s_provider=provider,
    depends_on=[minikube_start, metaflow_namespace],
    namespace=metaflow_namespace,
)
# Deploy postgres
postgres_chart = deploy_postgres_component(
    k8s_provider=provider,
    namespace=metaflow_namespace,
    cfg=cfg,
    depends_on=[minikube_start, metaflow_namespace],
)

# Deploy arc controller and scale set
arc_component = deploy_arc_components(
    k8s_provider=provider,
    depends_on=[minikube_start, metaflow_namespace],
)

# Deploy metaflow
metaflow_chart, metaflow_config = deploy_metaflow_component(
    k8s_provider=provider,
    namespace=metaflow_namespace,
    cfg=cfg,
    depends_on=[
        minikube_start,
        metaflow_namespace,
        minio_chart,
        postgres_chart,
    ],
)
# Deploy monitoring components -> Prometheus, Grafana
prometheus_chart, grafana_chart = deploy_monitoring_components(
    k8s_provider=provider,
    cfg=cfg,
    depends_on=[
        minikube_start,
    ],
)
# Deploy argo components
argo_config, argo_workflows_chart, argo_events_chart = deploy_argo_components(
    cfg=cfg,
    k8s_provider=provider,
    namespace=metaflow_namespace,
    depends_on=[
        minikube_start,
        metaflow_namespace,
        prometheus_chart,
        grafana_chart,
        metaflow_chart,
        minio_chart,
        postgres_chart,
        arc_component,
    ],
)
# Deploy metaflow webhook components
deploy_metaflow_webhook_components(
    depends_on=[
        minikube_start,
        metaflow_namespace,
        prometheus_chart,
        grafana_chart,
        metaflow_chart,
        minio_chart,
        postgres_chart,
        arc_component,
        argo_workflows_chart,
        argo_events_chart,
    ],
    k8s_provider=provider,
    namespace=metaflow_namespace,
)

# Finally create metaflow config
deploy_metaflow_config_component(
    metaflow_config=metaflow_config,
    argo_config=argo_config,
    depends_on=[
        minikube_start,
        metaflow_namespace,
        prometheus_chart,
        grafana_chart,
        metaflow_chart,
        arc_component,
        postgres_chart,
        minio_chart,
    ],
)
# Deploy annotator component
argilla_chart = deploy_argilla_component(
    cfg=cfg,
    k8s_provider=provider,
    argilla_access_key_identifier="argilla_username",
    argilla_secret_key_identifier="argilla_password",
    argilla_api_key_identifier="argilla_api_key",
    depends_on=[
        minikube_start,
        metaflow_namespace,
        prometheus_chart,
        grafana_chart,
        metaflow_chart,
        arc_component,
        postgres_chart,
        minio_chart,
    ],
)
