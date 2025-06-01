#!/bin/bash

# ZenML Pipeline Runner Script
# Usage: ./run_pipeline.sh <pipeline_name>

# Check if pipeline name is provided
if [ $# -eq 0 ]; then
    echo "Error: Please provide a pipeline name"
    echo "Usage: $0 <pipeline_name>"
    echo "Example: $0 training_pipeline"
    exit 1
fi

PIPELINE_NAME=$1
# Navigate to root directory (parent of scripts folder)
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIPELINE_PATH="$ROOT_DIR/pbd/pipelines/${PIPELINE_NAME}"
VENV_PATH="${PIPELINE_PATH}/.venv"

# Check if pipeline directory exists
if [ ! -d "$PIPELINE_PATH" ]; then
    echo "Error: Pipeline directory '$PIPELINE_PATH' not found"
    echo "Available pipelines:"
    ls -1 "$ROOT_DIR/pbd/pipelines/" 2>/dev/null | grep -v __pycache__ || echo "No pipelines found"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at '$VENV_PATH'"
    exit 1
fi

# Check if activation script exists
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "Error: Virtual environment activation script not found at '$VENV_PATH/bin/activate'"
    exit 1
fi

echo "Activating virtual environment for $PIPELINE_NAME..."
echo "Pipeline path: $PIPELINE_PATH"
echo "Venv path: $VENV_PATH"
echo "----------------------------------------"

# Activate virtual environment and run the pipeline
cd "$ROOT_DIR"
source "$VENV_PATH/bin/activate"

# Check if activation was successful
if [ "$VIRTUAL_ENV" != "" ]; then
    echo "Virtual environment activated: $VIRTUAL_ENV"
    echo "Running ZenML pipeline..."
    echo "Command: python3 -m pbd.pipelines.${PIPELINE_NAME}.pipelines"
    echo "----------------------------------------"

    # Execute the pipeline
    python3 -m pbd.pipelines.${PIPELINE_NAME}.pipelines

    # Capture exit code
    EXIT_CODE=$?

    echo "----------------------------------------"
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Pipeline completed successfully"
    else
        echo "Pipeline failed with exit code: $EXIT_CODE"
    fi

    # Deactivate virtual environment
    deactivate

    exit $EXIT_CODE
else
    echo "Error: Failed to activate virtual environment"
    exit 1
fi
