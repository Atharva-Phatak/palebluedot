from zenml.integrations.kubernetes.flavors import KubernetesStepOperatorSettings
from zenml.config import DockerSettings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

pod_settings = KubernetesPodSettings(resources ={
            "requests": {
                "cpu": "2",
                "memory": "512Mi"
            },
            "limits": {
                "cpu": "4",
                "memory": "2Gi"
            }
        },
        env = [
            {
                "name": "AWS_ACCESS_KEY_ID",
                "value" : "minio@1234"
            },
            {
                "name" : "AWS_SECRET_ACCESS_KEY",
                "value" : "minio@local1234"
            },
            {
                "name" : "AWS_REGION",
                "value" : "us-east-1"
            }
        ])

k8s_operator_settings = KubernetesStepOperatorSettings(
    pod_settings=pod_settings,
)
docker_settings = DockerSettings(
    parent_image="ghcr.io/atharva-phatak/pbd-data_processing:latest",
    skip_build=True
)