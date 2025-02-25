terraform {
  backend "local" {}
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.35.1"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.2"
    }
  }
}

locals {
  addons_string = join(" --addons=", var.addons)
}

resource "null_resource" "minikube_cluster" {
  provisioner "local-exec" {
    command = <<-EOT
      minikube start \
        --cpus=${var.cpus} \
        --memory=${var.memory} \
        --addons=${local.addons_string}
    EOT
  }

  provisioner "local-exec" {
    when    = destroy
    command = "minikube delete"
  }
}
