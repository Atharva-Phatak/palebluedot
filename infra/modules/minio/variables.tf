variable "minio_storage_path" {
  description = "Path for MinIO storage on the host"
  type        = string
  default     = "/home/atharvaphatak/Desktop/fsml/data"
}

variable "minio_pv_name" {
  description = "Persistent Volume name"
  type        = string
  default     = "minio-pv"
}

variable "minio_pvc_name" {
  description = "Persistent Volume Claim name"
  type        = string
  default     = "minio-pv-claim"
}

variable "minio_deployment_name" {
  description = "MinIO Deployment name"
  type        = string
  default     = "minio-deployment"
}

variable "minio_service_name" {
  description = "MinIO Service name"
  type        = string
  default     = "minio-service"
}

variable "minio_ingress_host" {
  description = "Ingress host for MinIO"
  type        = string
  default     = "fsml-minio.info"
}

variable "minio_access_key" {
  description = "MinIO Access Key"
  type        = string
  default     = "minio"
}

variable "minio_secret_key" {
  description = "MinIO Secret Key"
  type        = string
  default     = "minio123"
}
