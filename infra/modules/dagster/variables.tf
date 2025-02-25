variable "namespace" {
  description = "Kubernetes namespace for Dagster"
  type        = string
  default     = "dagster"
}

variable "chart_version" {
  description = "Dagster Helm chart version"
  type        = string
  default     = "1.10.2"
}
