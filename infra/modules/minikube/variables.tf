variable "kubernetes_version" {
  description = "Kubernetes version to install"
  type        = string
  default     = "v2.35.1"
}

variable "cpus" {
  description = "Number of CPUs to allocate to Minikube"
  type        = number
  default     = 4
}

variable "memory" {
  description = "Amount of memory to allocate to Minikube"
  type        = string
  default     = "8192mb"
}

variable "addons" {
  description = "List of Minikube addons to enable"
  type        = list(string)
  default     = ["ingress"]
}
