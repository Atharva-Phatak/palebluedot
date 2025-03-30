#!/bin/bash

# Set strict mode
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error

export AWS_ACCESS_KEY_ID="minio@1234"
export AWS_SECRET_ACCESS_KEY="minio@local1234"

echo "Registering Minio artifact store..."
zenml artifact-store register minio_store  --flavor=s3  --path=s3://zenml-bucket  --client_kwargs='{"endpoint_url": "http://fsml-minio.info", "region_name": "us-east-1"}'


echo "Registering Kubernetes orchestrator..."
zenml orchestrator register minikube_orchestrator --flavor=kubernetes --kubernetes_context="minikube"

echo "Adding github repo"
zenml code-repository register pbd --type=github --owner=Atharva-Phatak --repository=palebluedot --token={{GITHUB_TOKEN}}


zenml stack register mk_stack -o minikube_orchestrator -a minio_store  --set


echo "Setup completed successfully!"