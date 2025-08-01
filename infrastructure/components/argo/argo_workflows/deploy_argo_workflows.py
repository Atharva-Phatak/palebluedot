import pulumi
import pulumi_kubernetes as k8s


def deploy_argo_workflows(
    depends_on: list,
    k8s_provider: k8s.Provider,
    namespace: str,
):
    argo_chart = k8s.helm.v3.Chart(
        "argo-workflows",
        k8s.helm.v3.ChartOpts(
            chart="argo-workflows",
            version="0.41.2",  # Use a specific version or remove for latest
            fetch_opts=k8s.helm.v3.FetchOpts(
                repo="https://argoproj.github.io/argo-helm"
            ),
            namespace=namespace,
            values={
                "server": {
                    "extraArgs": ["--auth-mode=server"],
                    "livenessProbe": {"initialDelaySeconds": 1},
                    "readinessProbe": {"initialDelaySeconds": 1},
                    "resources": {
                        "requests": {"memory": "128Mi", "cpu": "50m"},
                        "limits": {"memory": "256Mi", "cpu": "100m"},
                    },
                    "ingress": {
                        "enabled": True,
                        "ingressClassName": "nginx",
                        "annotations": {
                            "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                            "nginx.ingress.kubernetes.io/rewrite-target": "/",
                            "nginx.ingress.kubernetes.io/proxy-body-size": "64m",
                            "nginx.ingress.kubernetes.io/proxy-connect-timeout": "300",
                            "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                            "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
                        },
                        "hosts": ["argoworkflows.palebluedot.io"],
                    },
                },
                "controller": {
                    "resources": {
                        "requests": {"memory": "128Mi", "cpu": "50m"},
                        "limits": {"memory": "256Mi", "cpu": "100m"},
                    },
                },
                "workflow": {
                    "serviceAccount": {"create": True},
                    "rbac": {"create": True},
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            depends_on=depends_on,
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="15m"),
        ),
    )
    _ = k8s.rbac.v1.Role(
        "argo-workflowtaskresults-role",
        metadata={
            "name": "argo-workflowtaskresults-role",
            "namespace": namespace,
        },
        rules=[
            {
                "apiGroups": ["argoproj.io"],
                "resources": ["workflowtaskresults"],
                "verbs": ["create", "patch", "get", "list"],
            }
        ],
    )

    # Create RoleBinding
    _ = k8s.rbac.v1.RoleBinding(
        "default-argo-workflowtaskresults-binding",
        metadata={
            "name": "default-argo-workflowtaskresults-binding",
            "namespace": namespace,
        },
        subjects=[
            {
                "kind": "ServiceAccount",
                "name": "default",
                "namespace": namespace,
            }
        ],
        role_ref={
            "kind": "Role",
            "name": "argo-workflowtaskresults-role",
            "apiGroup": "rbac.authorization.k8s.io",
        },
    )
    pulumi.export("argo_chart", argo_chart.ready)
    return argo_chart
