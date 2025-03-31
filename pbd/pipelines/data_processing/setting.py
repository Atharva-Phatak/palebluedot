from zenml.integrations.kubernetes.flavors import KubernetesStepOperatorSettings
from zenml.config import DockerSettings

pod_settings = KubernetesStepOperatorSettings(
    pod_settings={
        "resources": {
            "requests": {
                "cpu": "2",
                "memory": "512Mi"
            },
            "limits": {
                "cpu": "4",
                "memory": "2Gi"
            }
        },
        "env_from": [
            {
                "secretRef": {
                    "name": "aws-credentials",
                }
            }
        ],

    },
    kubernetes_namespace="pipeline-namespace",
)

docker_settings = DockerSettings(
    parent_image="ghcr.io/atharva-phatak/pbd-data_processing:latest",
    skip_build=True
)