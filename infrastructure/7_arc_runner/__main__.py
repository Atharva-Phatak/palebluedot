from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.config import load_config
from infrastructure.helper.namespace import create_namespace
from infrastructure.helper.secrets import create_k8s_gh_secret
from infrastructure.components.arc_scale_set.gh_runners import (
    deploy_arc_scale_set,
    deploy_arc_controller,
)

provider = get_k8s_provider()
config = load_config()
namespace = create_namespace(
    provider=provider,
    namespace="arc-ns",
)
gh_secret = create_k8s_gh_secret(
    k8s_provider=provider,
    depends_on=[namespace],
    namespace=namespace,
    project_id=config.infiscal_project_id,
    environment_slug="dev",
)
arc_controller_resource = deploy_arc_controller(
    depends_on=[gh_secret, namespace],
    namespace=namespace,
    k8s_provider=provider,
)

# Deploy ARC Scale Set
arc_scale_set_resource = deploy_arc_scale_set(
    depends_on=[arc_controller_resource, gh_secret, namespace],
    namespace=namespace,
    k8s_provider=provider,
    github_secret=gh_secret,
)
