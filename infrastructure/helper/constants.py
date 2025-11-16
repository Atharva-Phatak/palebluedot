from enum import StrEnum, auto
from pydantic import BaseModel


class InfrastructureConfig(BaseModel):
    pv_name: str
    pvc_name: str
    model_pv_name: str
    model_pvc_name: str
    data_bucket: str
    zenml_bucket: str
    minio_storage_capacity: str
    model_storage_capacity: str
    storage_path: str
    model_storage_path: str
    # argilla_mount_path: str
    # redis_mount_path: str
    # redis_replica_mount_path: str
    sql_host_path: str
    minikube_cpus: int
    minikube_memory: str
    minikube_disk_size: str
    minikube_addons: str
    minikube_gpus: str
    infiscal_project_id: str
    minio_ingress_host: str
    minio_deployment_name: str
    minio_service_name: str


class SecretNames(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        # Automatically use the lowercase member name as the value
        return name.lower()

    MINIO_ACCESS_KEY = auto()
    MINIO_SECRET_KEY = auto()
    MYSQL_PASSWORD = auto()
    MYSQL_USER = auto()
    SLACK_TOKEN = auto()
    ZENML_JWT_SECRET = auto()
