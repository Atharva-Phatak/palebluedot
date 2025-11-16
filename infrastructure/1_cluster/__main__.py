from infrastructure.components.cluster.minikube import start_minikube
from infrastructure.helper.config import load_config
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.helper.namespace import create_namespace
import pulumi

# Load configuration
cfg = load_config()

# Start Minikube with the specified configuration
minikube_start = start_minikube(
    n_cpus=cfg.minikube_cpus,
    memory=cfg.minikube_memory,
    addons=cfg.minikube_addons,
    gpus=cfg.minikube_gpus,
    disk_size=cfg.minikube_disk_size,
    models_mount_path=cfg.model_storage_path,
)
provider = get_k8s_provider(depends_on=[minikube_start])
zenml_namespace = create_namespace(
    namespace="zenml",
    provider=provider,
    depends_on=[minikube_start],
)
pulumi.export("namespace", zenml_namespace.metadata["name"])
