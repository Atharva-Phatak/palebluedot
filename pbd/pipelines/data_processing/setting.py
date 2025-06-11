"""
Settings for Data Processing Pipeline Orchestration

This module defines Kubernetes and Docker settings for orchestrating the data processing pipeline.
It configures resource requests/limits, environment variables, and image settings for ZenML steps and orchestrator.

Attributes:
    step_pod_settings (KubernetesPodSettings): Pod settings for pipeline steps.
    orchestrator_pod_settings (KubernetesPodSettings): Pod settings for the orchestrator.
    k8s_operator_settings (KubernetesOrchestratorSettings): Kubernetes operator settings for ZenML.
    docker_settings (DockerSettings): Docker image settings for ZenML pipeline.
"""

from zenml.integrations.kubernetes.flavors import KubernetesOrchestratorSettings
from zenml.config import DockerSettings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

step_pod_settings = KubernetesPodSettings(
    resources={
        "requests": {"cpu": "4", "memory": "2Gi"},
        "limits": {"cpu": "6", "memory": "3Gi"},
    },
    env_from=[{"secretRef": {"name": "aws-credentials"}}],
    labels={"app": "youtube-scraper-pipeline", "component": "step"},
)

orchestrator_pod_settings = KubernetesPodSettings(
    resources={
        "requests": {"cpu": "2", "memory": "70Mi"},
        "limits": {"cpu": "4", "memory": "256Mi"},
    },
    env_from=[{"secretRef": {"name": "aws-credentials"}}],
    labels={"app": "zenml-orchestrator", "component": "orchestrator"},
)


k8s_operator_settings = KubernetesOrchestratorSettings(
    pod_settings=step_pod_settings,
    orchestrator_pod_settings=orchestrator_pod_settings,
)
docker_settings = DockerSettings(
    parent_image="ghcr.io/atharva-phatak/pbd-data_processing:latest", skip_build=True
)
