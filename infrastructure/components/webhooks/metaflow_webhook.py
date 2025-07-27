import pulumi
import pulumi_kubernetes as k8s


def deploy_metaflow_webhook(
    namespace: str,
    provider: k8s.Provider,
    depends_on: list = None,
):
    app_labels = {"app": "metaflow-webhook"}

    deployment = k8s.apps.v1.Deployment(
        "metaflow-webhook",
        metadata={
            "namespace": namespace,
            "name": "metaflow-webhook",  # Added explicit name
        },
        spec={
            "replicas": 1,  # Added explicit replica count
            "selector": {"matchLabels": app_labels},
            "template": {
                "metadata": {"labels": app_labels},
                "spec": {
                    "containers": [
                        {
                            "name": "webhook",
                            "image": "ghcr.io/atharva-phatak/metaflow_webhook:latest",
                            "imagePullPolicy": "Always",
                            "ports": [
                                {"containerPort": 8000, "name": "http"}
                            ],  # Added port name
                            # Added resource limits/requests (recommended)
                            "resources": {
                                "requests": {"cpu": "50m", "memory": "128Mi"},
                                "limits": {"cpu": "500m", "memory": "512Mi"},
                            },
                            # Added health checks (recommended for production)
                            "livenessProbe": {
                                "httpGet": {"path": "/health", "port": 8000},
                                "initialDelaySeconds": 30,
                                "periodSeconds": 10,
                            },
                            "readinessProbe": {
                                "httpGet": {"path": "/ready", "port": 8000},
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5,
                            },
                        }
                    ]
                },
            },
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on or [],  # Handle None case
        ),
    )

    service = k8s.core.v1.Service(
        "metaflow-webhook-service",
        metadata={
            "namespace": namespace,
            "name": "metaflow-webhook-service",  # Made service name more explicit
        },
        spec={
            "type": "ClusterIP",
            "ports": [
                {"port": 12000, "targetPort": 8000, "name": "http"}
            ],  # Added port name
            "selector": app_labels,
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=(depends_on or []) + [deployment],  # Handle None case
        ),
    )

    return deployment, service
