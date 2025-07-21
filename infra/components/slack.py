from applications.secret_manager.secrets import create_slack_secret
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import Namespace


def deploy_slack_secret(
    depends_on: list,
    namespace: Namespace,
    k8s_provider: k8s.Provider,
    project_id: str,
):
    slack_secret = create_slack_secret(
        namespace=namespace,
        depends_on=depends_on,
        k8s_provider=k8s_provider,
        project_id=project_id,
        environment_slug="dev",
    )
    return slack_secret
