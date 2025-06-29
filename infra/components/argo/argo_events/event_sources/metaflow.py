import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import Namespace


def deploy_metaflow_event_source(
    namespace: Namespace,
    depends_on: list,
    provider: k8s.Provider = None,
):
    # EventSource webhook
    metaflow_event_source = k8s.apiextensions.CustomResource(
        "event-source",
        api_version="argoproj.io/v1alpha1",
        kind="EventSource",
        metadata={
            "name": "argo-events-webhook",
            "namespace": namespace.metadata["name"],
        },
        spec={
            "template": {
                "container": {
                    "resources": {
                        "requests": {"cpu": "25m", "memory": "50Mi"},
                        "limits": {"cpu": "25m", "memory": "50Mi"},
                    }
                }
            },
            "service": {"ports": [{"port": 12000, "targetPort": 12000}]},
            "webhook": {
                "metaflow-event": {
                    "port": "12000",
                    "endpoint": "/metaflow-event",
                    "method": "POST",
                }
            },
        },
        opts=pulumi.ResourceOptions(
            depends_on=depends_on,
            provider=provider,
            custom_timeouts=pulumi.CustomTimeouts(create="30m"),
        ),
    )
    return metaflow_event_source
