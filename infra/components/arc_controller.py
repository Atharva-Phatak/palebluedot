import pulumi_kubernetes as k8s
from applications.gh_runners.arc_controller import deploy_arc_controller
from applications.gh_runners.arc_scale_set import deploy_arc_scale_set
from applications.secret_manager.secrets import create_gh_secret
from applications.k8s.namespace import create_namespace


def deploy_arc_components(k8s_provider: k8s.Provider, depends_on: list):
    namespace = create_namespace(
        provider=k8s_provider,
        namespace="arc-ns",
        depends_on=depends_on,
    )
    gh_secret = create_gh_secret(
        k8s_provider=k8s_provider,
        depends_on=depends_on,
        namespace=namespace,
    )
    arc_controller_resource = deploy_arc_controller(
        depends_on=depends_on,
        namespace=namespace,
        k8s_provider=k8s_provider,
    )

    # Deploy ARC Scale Set
    arc_scale_set_resource = deploy_arc_scale_set(
        depends_on=depends_on + [arc_controller_resource, gh_secret, namespace],
        namespace=namespace,
        k8s_provider=k8s_provider,
        github_secret=gh_secret,
    )
    return arc_scale_set_resource
