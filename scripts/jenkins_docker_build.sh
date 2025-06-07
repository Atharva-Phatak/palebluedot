#!/bin/bash
# Jenkins-specific lightweight build & push script for PBD pipelines
# Usage: PIPELINE_NAME=ocr_engine ./scripts/jenkins_build.sh

set -e  # Exit on any error

# Validate input
if [ -z "$PIPELINE_NAME" ]; then
  echo "❌ Error: PIPELINE_NAME environment variable not set."
  echo "Usage: PIPELINE_NAME=ocr_engine ./scripts/jenkins_build.sh"
  exit 1
fi

USERNAME="Atharva-Phatak"
TAG="latest"
IMAGE_NAME="ghcr.io/${USERNAME,,}/pbd-${PIPELINE_NAME}:${TAG}"
DOCKERFILE_PATH="pbd/pipelines/${PIPELINE_NAME}/Dockerfile"

# Ensure Dockerfile exists
if [ ! -f "$DOCKERFILE_PATH" ]; then
  echo "❌ Error: Dockerfile not found at $DOCKERFILE_PATH"
  exit 1
fi

echo "📦 Building and pushing Docker image for: $PIPELINE_NAME"

# Login to GHCR
echo "$GHCR_PAT" | docker login ghcr.io -u "$USERNAME" --password-stdin

# Build and push
docker build -f "$DOCKERFILE_PATH" -t "$IMAGE_NAME" .
docker push "$IMAGE_NAME"

echo "✅ Done: $IMAGE_NAME pushed to GHCR."
