from applications.k8s.minikube import start_minikube
from applications.k8s.provider import get_k8s_provider


def deploy_minikube_cluster(cfg):
    minikube_start = start_minikube(
        n_cpus=cfg.minikube_cpus,
        memory=cfg.minikube_memory,
        addons=cfg.minikube_addons,
        gpus=cfg.minikube_gpus,
        disk_size=cfg.minikube_disk_size,
        models_mount_path=cfg.model_storage_path,
    )

    k8s_provider = get_k8s_provider(depends_on=[minikube_start])
    return k8s_provider, minikube_start
