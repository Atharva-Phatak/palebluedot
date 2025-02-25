include "root" {
  path = find_in_parent_folders()
}

dependency "minikube" {
  config_path = "../1_minikube"
  mock_outputs = {
    minikube_output = "mock-minikube-output"
  }

}

terraform {
  source = "../../../modules/dagster"
}
