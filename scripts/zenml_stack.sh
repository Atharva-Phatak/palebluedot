#!/bin/bash

# Set strict mode
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error

echo "Registering Minio artifact store..."
zenml artifact-store register minio_store  --flavor=s3  --path=s3://zenml-bucket  --client_kwargs='{"endpoint_url": "http://fsml-minio.info", "region_name": "us-east-1"}'


echo "Registering Kubernetes orchestrator..."
zenml orchestrator register minikube_orchestrator --flavor=kubernetes --kubernetes_context="minikube"

zenml container-registry register ghcr --flavor=github --uri=ghcr.io/atharva-phatak

# Get the current active stack

zenml stack register mk_stack -o minikube_orchestrator -a minio_store -c ghcr  --set

echo "Setup completed successfully!"