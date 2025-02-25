output "namespace" {
  description = "The Kubernetes namespace Dagster is deployed in"
  value       = kubernetes_namespace.dagster.metadata[0].name
}
