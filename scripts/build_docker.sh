#!/bin/bash
# Docker Build and Push Script for PBD Pipelines with Timing
# Usage: ./build_and_push.sh <pipeline_name> [tag]

# Function to format duration in human readable format
format_duration() {
    local duration=$1
    local hours=$((duration / 3600))
    local minutes=$(((duration % 3600) / 60))
    local seconds=$((duration % 60))

    if [ $hours -gt 0 ]; then
        printf "%dh %dm %ds" $hours $minutes $seconds
    elif [ $minutes -gt 0 ]; then
        printf "%dm %ds" $minutes $seconds
    else
        printf "%ds" $seconds
    fi
}

# Start total time tracking
SCRIPT_START_TIME=$(date +%s)
echo "⏱️  Starting pipeline build and push at $(date)"
echo "========================================"

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
VALIDATION_START_TIME=$(date +%s)
if [ ! -f "$DOCKERFILE_PATH" ]; then
    echo "Error: Dockerfile not found at '$DOCKERFILE_PATH'"
    echo "Available pipelines:"
    ls -1 "$ROOT_DIR/pbd/pipelines/" 2>/dev/null | grep -v __pycache__ || echo "No pipelines found"
    exit 1
fi
VALIDATION_END_TIME=$(date +%s)
VALIDATION_DURATION=$((VALIDATION_END_TIME - VALIDATION_START_TIME))

# Change to root directory for build context
cd "$ROOT_DIR"

echo "🔨 Building Docker image..."
echo "Command: docker build --no-cache -f pbd/pipelines/${PIPELINE_NAME}/Dockerfile -t ${IMAGE_NAME} ."
echo "----------------------------------------"

# Build the Docker image with timing
BUILD_START_TIME=$(date +%s)
docker build --no-cache -f "pbd/pipelines/${PIPELINE_NAME}/Dockerfile" -t "$IMAGE_NAME" .
BUILD_EXIT_CODE=$?
BUILD_END_TIME=$(date +%s)
BUILD_DURATION=$((BUILD_END_TIME - BUILD_START_TIME))

# Check if build was successful
if [ $BUILD_EXIT_CODE -ne 0 ]; then
    echo "❌ Error: Docker build failed with exit code: $BUILD_EXIT_CODE"
    echo "⏱️  Build duration: $(format_duration $BUILD_DURATION)"
    exit $BUILD_EXIT_CODE
fi

echo "----------------------------------------"
echo "✅ Docker build completed successfully!"
echo "⏱️  Build duration: $(format_duration $BUILD_DURATION)"
echo ""
echo "🚀 Pushing image to GitHub Container Registry..."
echo "Command: docker push ${IMAGE_NAME}"
echo "----------------------------------------"

# Push the Docker image with timing
PUSH_START_TIME=$(date +%s)
docker push "$IMAGE_NAME"
PUSH_EXIT_CODE=$?
PUSH_END_TIME=$(date +%s)
PUSH_DURATION=$((PUSH_END_TIME - PUSH_START_TIME))

# Calculate total time
SCRIPT_END_TIME=$(date +%s)
TOTAL_DURATION=$((SCRIPT_END_TIME - SCRIPT_START_TIME))

# Check if push was successful
if [ $PUSH_EXIT_CODE -eq 0 ]; then
    echo "----------------------------------------"
    echo "✅ Success! Image pushed successfully"
    echo "Image: $IMAGE_NAME"
    echo "Registry URL: https://github.com/${USERNAME}/pkgs/container/pbd-${PIPELINE_NAME}"
    echo ""
    echo "📊 TIMING SUMMARY"
    echo "==================="
    echo "⏱️  Validation time: $(format_duration $VALIDATION_DURATION)"
    echo "🔨 Build time:      $(format_duration $BUILD_DURATION)"
    echo "🚀 Push time:       $(format_duration $PUSH_DURATION)"
    echo "📈 Total time:      $(format_duration $TOTAL_DURATION)"
    echo "🕐 Completed at:    $(date)"
    echo ""
    echo "To pull this image:"
    echo "docker pull $IMAGE_NAME"
else
    echo "❌ Error: Docker push failed with exit code: $PUSH_EXIT_CODE"
    echo "⏱️  Push duration: $(format_duration $PUSH_DURATION)"
    echo "📊 Partial timing summary:"
    echo "   Validation: $(format_duration $VALIDATION_DURATION)"
    echo "   Build:      $(format_duration $BUILD_DURATION)"
    echo "   Total:      $(format_duration $TOTAL_DURATION)"
    echo ""
    echo "Make sure you're logged in to GHCR with: docker login ghcr.io"
    exit $PUSH_EXIT_CODE
fi
