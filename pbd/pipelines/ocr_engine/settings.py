from zenml.config import DockerSettings
from zenml.integrations.kubernetes.flavors import KubernetesOrchestratorSettings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

step_pod_settings = KubernetesPodSettings(
    resources={
        "requests": {"cpu": "4", "memory": "10Gi", "nvidia.com/gpu": "1"},
        "limits": {"cpu": "6", "memory": "18Gi", "nvidia.com/gpu": "1"},
    },
    volumes=[
        {"name": "model-volume", "persistentVolumeClaim": {"claimName": "mk-model-pvc"}}
    ],
    volume_mounts=[
        {
            "name": "model-volume",
            "mountPath": "/models",
        }
    ],
    env_from=[{"secretRef": {"name": "aws-credentials"}}],
    labels={"app": "ocr_pipelines", "component": "step"},
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
    pod_startup_timeout=1200,  # 20 minutes
)
docker_settings = DockerSettings(
    parent_image="ghcr.io/atharva-phatak/pbd-ocr_engine:latest", skip_build=True
)
