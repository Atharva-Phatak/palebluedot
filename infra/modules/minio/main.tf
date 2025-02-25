terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.0.0"
    }
  }
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "minikube"
}

resource "kubernetes_persistent_volume" "minio_pv" {
  metadata {
    name = var.minio_pv_name
  }

  spec {
    capacity = {
      storage = "10Gi"
    }
    access_modes                     = ["ReadWriteMany"]
    persistent_volume_reclaim_policy = "Retain"
    storage_class_name               = "manual"

    persistent_volume_source {
      host_path {
        path = var.minio_storage_path
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "minio_pvc" {
  metadata {
    name = var.minio_pvc_name
  }

  spec {
    access_modes = ["ReadWriteMany"]
    resources {
      requests = {
        storage = "10Gi"
      }
    }
    storage_class_name = "manual"
  }
}

resource "kubernetes_deployment" "minio" {
  metadata {
    name = var.minio_deployment_name
  }

  spec {
    selector {
      match_labels = {
        app = "minio"
      }
    }
    strategy {
      type = "Recreate"
    }
    template {
      metadata {
        labels = {
          app = "minio"
        }
      }
      spec {
        host_network   = true
        restart_policy = "Always"

        volume {
          name = "storage"
          persistent_volume_claim {
            claim_name = var.minio_pvc_name
          }
        }

        container {
          name  = "minio"
          image = "minio/minio:latest"
          args  = ["server", "/data"]

          env {
            name  = "MINIO_ACCESS_KEY"
            value = var.minio_access_key
          }

          env {
            name  = "MINIO_SECRET_KEY"
            value = var.minio_secret_key
          }

          port {
            container_port = 9000
          }

          volume_mount {
            name       = "storage"
            mount_path = "/data"
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "minio_service" {
  metadata {
    name = var.minio_service_name
    labels = {
      app = "minio"
    }
  }
  spec {
    selector = {
      app = "minio"
    }
    port {
      name        = "minio-port"
      protocol    = "TCP"
      port        = 9000
      target_port = 9000
    }
    type = "ClusterIP" # Changed to ClusterIP since we're using Ingress
  }
}

resource "kubernetes_ingress_v1" "minio_ingress" {
  metadata {
    name = "minio-ingress"
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
      host = var.minio_ingress_host
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = var.minio_service_name
              port {
                number = 9000
              }
            }
          }
        }
      }
    }
  }
}
