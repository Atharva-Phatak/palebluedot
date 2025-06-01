#!/bin/bash

# Docker Build and Push Script for PBD Pipelines
# Usage: ./build_and_push.sh <pipeline_name> [tag]

# Check if pipeline name is provided
if [ $# -eq 0 ]; then
    echo "Error: Please provide a pipeline name"
    echo "Usage: $0 <pipeline_name> [tag]"
    echo "Example: $0 ocr_engine latest"
    echo "         $0 training_pipeline v1.0.0"
    exit 1
fi

PIPELINE_NAME=$1
TAG=${2:-latest}  # Default to 'latest' if no tag provided
USERNAME="atharva-phatak"

# Navigate to root directory (parent of scripts folder)
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DOCKERFILE_PATH="$ROOT_DIR/pbd/pipelines/${PIPELINE_NAME}/Dockerfile"
IMAGE_NAME="ghcr.io/${USERNAME}/pbd-${PIPELINE_NAME}:${TAG}"

echo "Pipeline: $PIPELINE_NAME"
echo "Tag: $TAG"
echo "Image name: $IMAGE_NAME"
echo "Dockerfile path: $DOCKERFILE_PATH"
echo "Root directory: $ROOT_DIR"
echo "----------------------------------------"

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE_PATH" ]; then
    echo "Error: Dockerfile not found at '$DOCKERFILE_PATH'"
    echo "Available pipelines:"
    ls -1 "$ROOT_DIR/pbd/pipelines/" 2>/dev/null | grep -v __pycache__ || echo "No pipelines found"
    exit 1
fi

# Change to root directory for build context
cd "$ROOT_DIR"

echo "Building Docker image..."
echo "Command: docker build --no-cache -f pbd/pipelines/${PIPELINE_NAME}/Dockerfile -t ${IMAGE_NAME} ."
echo "----------------------------------------"

# Build the Docker image
docker build --no-cache -f "pbd/pipelines/${PIPELINE_NAME}/Dockerfile" -t "$IMAGE_NAME" .

# Check if build was successful
BUILD_EXIT_CODE=$?
if [ $BUILD_EXIT_CODE -ne 0 ]; then
    echo "Error: Docker build failed with exit code: $BUILD_EXIT_CODE"
    exit $BUILD_EXIT_CODE
fi

echo "----------------------------------------"
echo "Docker build completed successfully!"
echo "Pushing image to GitHub Container Registry..."
echo "Command: docker push ${IMAGE_NAME}"
echo "----------------------------------------"

# Push the Docker image
docker push "$IMAGE_NAME"

# Check if push was successful
PUSH_EXIT_CODE=$?
if [ $PUSH_EXIT_CODE -eq 0 ]; then
    echo "----------------------------------------"
    echo "✅ Success! Image pushed successfully"
    echo "Image: $IMAGE_NAME"
    echo "Registry URL: https://github.com/${USERNAME}/pkgs/container/pbd-${PIPELINE_NAME}"
    echo ""
    echo "To pull this image:"
    echo "docker pull $IMAGE_NAME"
else
    echo "Error: Docker push failed with exit code: $PUSH_EXIT_CODE"
    echo "Make sure you're logged in to GHCR with: docker login ghcr.io"
    exit $PUSH_EXIT_CODE
fi
