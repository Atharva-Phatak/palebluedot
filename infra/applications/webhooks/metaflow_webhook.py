import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import Namespace


def deploy_metaflow_webhook(
    namespace: Namespace,
    provider: k8s.Provider,
    depends_on: list = None,
):
    app_labels = {"app": "metaflow-webhook"}

    deployment = k8s.apps.v1.Deployment(
        "metaflow-webhook",
        metadata={
            "namespace": namespace.metadata["name"],
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
            "namespace": namespace.metadata["name"],
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


def deploy_metaflow_webhook_ingress(
    provider: k8s.Provider, namespace: Namespace, depends_on: list = None
):
    domain = "mflownotif.192.168.49.2.traefik.me"  # replace with your Minikube IP
    metaflow_webhook_ingress = k8s.networking.v1.Ingress(
        "metaflow-webhook-ingress",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="metaflow-webhook-ingress",
            namespace=namespace.metadata["name"],
            annotations={
                "nginx.ingress.kubernetes.io/rewrite-target": "/",
                "kubernetes.io/ingress.class": "nginx",  # or "traefik"
                "cert-manager.io/cluster-issuer": "letsencrypt-staging",
                "nginx.ingress.kubernetes.io/ssl-redirect": "true",
                "nginx.ingress.kubernetes.io/proxy-body-size": "64m",
                "nginx.ingress.kubernetes.io/proxy-connect-timeout": "300",
                "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
            },
        ),
        spec=k8s.networking.v1.IngressSpecArgs(
            ingress_class_name="nginx",
            tls=[{"hosts": [domain], "secret_name": "metaflow-webhook-tls"}],
            rules=[
                k8s.networking.v1.IngressRuleArgs(
                    host=domain,
                    http=k8s.networking.v1.HTTPIngressRuleValueArgs(
                        paths=[
                            k8s.networking.v1.HTTPIngressPathArgs(
                                path="/",
                                path_type="Prefix",
                                backend=k8s.networking.v1.IngressBackendArgs(
                                    service={
                                        "name": "metaflow-webhook-service",
                                        "port": k8s.networking.v1.ServiceBackendPortArgs(
                                            number=12000
                                        ),
                                    }
                                ),
                            )
                        ]
                    ),
                )
            ],
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            custom_timeouts=pulumi.CustomTimeouts(create="20m"),
            depends_on=depends_on,
        ),
    )
    return metaflow_webhook_ingress
