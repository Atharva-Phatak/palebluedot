import pulumi
import pulumi_kubernetes as k8s


def deploy_argo_events(
    namespace: str,
    k8s_provider: k8s.Provider,
    depends_on: list = None,
):
    metaflow_argo_config = {}
    argo_events = k8s.helm.v3.Chart(
        "argo-events",
        k8s.helm.v3.ChartOpts(
            chart="argo-events",
            version="2.4.15",  # Optional: lock to a tested version
            fetch_opts=k8s.helm.v3.FetchOpts(
                repo="https://argoproj.github.io/argo-helm"
            ),
            namespace=namespace,
            values={
                "crds": {"install": True},
                "controller": {
                    "metrics": {"enabled": True},
                    "livenessProbe": {"initialDelaySeconds": 1},
                    "readinessProbe": {"initialDelaySeconds": 1},
                    "resources": {
                        "requests": {"memory": "64Mi", "cpu": "25m"},
                        "limits": {"memory": "128Mi", "cpu": "50m"},
                    },
                    "rbac": {
                        "enabled": True,
                        "namespaced": False,
                    },
                    "serviceAccount": {
                        "create": True,
                        "name": "argo-events-events-controller-sa",
                    },
                },
                "configs": {
                    "jetstream": {
                        "streamConfig": {
                            "maxAge": "72h",
                            "replicas": 3,
                        },
                        "versions": [
                            {
                                "version": "latest",
                                "natsImage": "nats:latest",
                                "metricsExporterImage": "natsio/prometheus-nats-exporter:latest",
                                "configReloaderImage": "natsio/nats-server-config-reloader:latest",
                                "startCommand": "/nats-server",
                            },
                            {
                                "version": "2.9.15",
                                "natsImage": "nats:2.9.15",
                                "metricsExporterImage": "natsio/prometheus-nats-exporter:latest",
                                "configReloaderImage": "natsio/nats-server-config-reloader:latest",
                                "startCommand": "/nats-server",
                            },
                        ],
                    }
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="15m"),
            depends_on=depends_on if depends_on else [],
        ),
    )

    # Additional ServiceAccount for workflows
    _ = k8s.core.v1.ServiceAccount(
        "operate-workflow-sa",
        metadata={
            "name": "operate-workflow-sa",
            "namespace": namespace,
        },
    )

    # Role and RoleBinding for operating workflows
    _ = k8s.rbac.v1.Role(
        "operate-workflow-role",
        metadata={
            "name": "operate-workflow-role",
            "namespace": namespace,
        },
        rules=[
            {
                "apiGroups": ["argoproj.io"],
                "resources": [
                    "workflows",
                    "workflowtemplates",
                    "cronworkflows",
                    "clusterworkflowtemplates",
                ],
                "verbs": ["*"],
            }
        ],
    )

    _ = k8s.rbac.v1.RoleBinding(
        "operate-workflow-role-binding",
        metadata={
            "name": "operate-workflow-role-binding",
            "namespace": namespace,
        },
        role_ref={
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "Role",
            "name": "operate-workflow-role",
        },
        subjects=[
            {
                "kind": "ServiceAccount",
                "name": "operate-workflow-sa",
                "namespace": namespace,
            }
        ],
    )

    # Role and binding to allow argo-workflows to view Argo Events
    _ = k8s.rbac.v1.Role(
        "view-events-role",
        metadata={"name": "view-events-role", "namespace": namespace},
        rules=[
            {
                "apiGroups": ["argoproj.io"],
                "resources": ["eventsources", "eventbuses", "sensors"],
                "verbs": ["get", "list", "watch"],
            }
        ],
    )

    _ = k8s.rbac.v1.RoleBinding(
        "view-events-role-binding",
        metadata={
            "name": "view-events-role-binding",
            "namespace": namespace,
        },
        role_ref={
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "Role",
            "name": "view-events-role",
        },
        subjects=[
            {
                "kind": "ServiceAccount",
                "name": "argo-workflows",
                "namespace": namespace,
            }
        ],
    )
    _ = k8s.apiextensions.CustomResource(
        "event-bus",
        api_version="argoproj.io/v1alpha1",
        kind="EventBus",
        metadata={"name": "default", "namespace": namespace},
        spec={
            "jetstream": {
                "version": "2.9.15",
                "replicas": 3,
                "containerTemplate": {
                    "resources": {
                        "limits": {"cpu": "100m", "memory": "128Mi"},
                        "requests": {"cpu": "100m", "memory": "128Mi"},
                    }
                },
                "cluster": {
                    "enabled": True,
                    "nodes": [
                        f"eventbus-default-js-{i}.eventbus-default-js-svc.metaflow.svc.cluster.local."
                        for i in range(3)
                    ],
                    "tls": {"enabled": False},
                },
            },
        },
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=depends_on or [],
        ),
    )

    metaflow_argo_config = {
        "METAFLOW_ARGO_EVENTS_EVENT": "metaflow-event",
        "METAFLOW_ARGO_EVENTS_EVENT_BUS": "default",
        "METAFLOW_ARGO_EVENTS_EVENT_SOURCE": "argo-events-webhook",
        "METAFLOW_ARGO_EVENTS_SERVICE_ACCOUNT": "operate-workflow-sa",
        "METAFLOW_ARGO_EVENTS_WEBHOOK_AUTH": "service",
        "METAFLOW_ARGO_EVENTS_INTERNAL_WEBHOOK_URL": "http://argo-events-webhook-eventsource-svc:12000/metaflow-event",
        "METAFLOW_ARGO_EVENTS_WEBHOOK_URL": "http://localhost:12000/metaflow-event",
    }
    pulumi.export("argo_events_chart", argo_events.ready)
    return argo_events, metaflow_argo_config
