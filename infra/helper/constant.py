from dataclasses import dataclass


@dataclass(frozen=True)
class Constants:
    pv_name: str = "mk-pv"
    pvc_name: str = "mk-pvc"
    storage_capacity: str = "200Gi"
    storage_path: str = "/home/atharvaphatak/Desktop/minikube_path/minio"
    minikube_cpus: int = 8
    minikube_memory: str = "20g"
    minikube_disk_size: str = "300GB"
    minikube_addons: str = "ingress,metrics-server"
    minikube_gpu: str = "all"
    infiscal_project_id: str = "ed73be73-bfc2-4950-a262-2cbd4a33d57f"
    minio_ingress_host: str = "fsml-minio.info"
    vllm_app: str = "qwen-vl-7b"
