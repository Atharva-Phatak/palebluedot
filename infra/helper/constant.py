from dataclasses import dataclass


@dataclass(frozen=True)
class Constants:
    pv_name: str = "mk-pv"
    pvc_name: str = "mk-pvc"
    model_pv_name: str = "mk-model-pv"
    model_pvc_name: str = "mk-model-pvc"
    mk_storage_capacity: str = "200Gi"
    model_storage_capacity: str = "100Gi"
    storage_path: str = "/home/atharvaphatak/Desktop/minikube_path/minio"
    model_storage_path: str = "/home/atharvaphatak/Desktop/models"
    sql_host_path: str = "/home/atharva/Desktop/minikube_path/mysql"
    minikube_cpus: int = 10
    minikube_memory: str = "25g"
    minikube_disk_size: str = "500GB"
    minikube_addons: str = "ingress,metrics-server"
    minikube_gpu: str = "all"
    infiscal_project_id: str = "ed73be73-bfc2-4950-a262-2cbd4a33d57f"
    minio_ingress_host: str = "fsml-minio.info"
