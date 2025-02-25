terraform {
  backend "local" {}
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12.1"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25.2"
    }
  }
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "minikube"
}

provider "helm" {
  kubernetes {
    config_path    = "~/.kube/config"
    config_context = "minikube"
  }
}

resource "kubernetes_namespace" "dagster" {
  metadata {
    name = var.namespace
  }
}

resource "helm_release" "dagster" {
  name       = "dagster"
  repository = "https://dagster-io.github.io/helm"
  chart      = "dagster"
  version    = var.chart_version
  namespace  = kubernetes_namespace.dagster.metadata[0].name

  values = [file("${path.module}/values.yaml")]
}

resource "kubernetes_ingress_v1" "dagster_ingress" {
  metadata {
    name      = "dagster-ingress"
    namespace = kubernetes_namespace.dagster.metadata[0].name
    annotations = {
      "nginx.ingress.kubernetes.io/rewrite-target"        = "/"
      "nginx.ingress.kubernetes.io/ssl-redirect"          = "false"
      "nginx.ingress.kubernetes.io/proxy-body-size"       = "64m"
      "nginx.ingress.kubernetes.io/proxy-connect-timeout" = "300"
      "nginx.ingress.kubernetes.io/proxy-send-timeout"    = "300"
      "nginx.ingress.kubernetes.io/proxy-read-timeout"    = "300"
    }
  }
  spec {
    rule {
      host = "fsml-dagster.info"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = "dagster-dagster-webserver" # This is the default service name created by Helm
              port {
                number = 80 # Default Dagster webserver port
              }
            }
          }
        }
      }
    }
  }

  depends_on = [helm_release.dagster] # Ensure Helm release is deployed first
}
