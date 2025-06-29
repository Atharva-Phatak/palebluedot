#!/bin/bash
# Metaflow Pipeline Runner Script (Kubernetes)
# Usage: ./run_pipeline.sh <pipeline_name>

set -e

if [ $# -eq 0 ]; then
    echo "❌ Error: Please provide a pipeline name"
    echo "Usage: $0 <pipeline_name>"
    exit 1
fi

PIPELINE_NAME=$1
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIPELINE_DIR="$ROOT_DIR/pbd/pipelines/$PIPELINE_NAME"
PIPELINE_FILE="$PIPELINE_DIR/pipelines.py"
CONFIG_FILE="$PIPELINE_DIR/config.json"
VENV_PATH="$PIPELINE_DIR/.venv"

# Validations
if [ ! -d "$PIPELINE_DIR" ]; then
    echo "❌ Error: Pipeline directory '$PIPELINE_DIR' not found"
    echo "Available pipelines:"
    ls -1 "$ROOT_DIR/pbd/pipelines/" | grep -v '__pycache__' || echo "No pipelines found"
    exit 1
fi

if [ ! -f "$PIPELINE_FILE" ]; then
    echo "❌ Error: Pipeline file '$PIPELINE_FILE' not found"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file '$CONFIG_FILE' not found"
    exit 1
fi

if [ ! -d "$VENV_PATH" ] || [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "❌ Error: Virtual environment missing or broken at '$VENV_PATH'"
    exit 1
fi

# Activate environment
echo "🔹 Activating virtual environment at $VENV_PATH..."
source "$VENV_PATH/bin/activate"

if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Error: Failed to activate virtual environment"
    exit 1
fi

# Run pipeline
cd "$PIPELINE_DIR"  # Change to pipeline directory first
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

echo "✅ Running Metaflow pipeline '$PIPELINE_NAME' with Kubernetes..."
echo "📍 Working directory: $(pwd)"
echo "📂 Root directory: $ROOT_DIR"
echo "🐍 Python path: $PYTHONPATH"
echo "----------------------------------------"

# Test Python path first
echo "🔍 Testing Python import..."
python -c "import sys; sys.path.insert(0, '$ROOT_DIR'); import pbd; print('✅ pbd module found')" || {
    echo "❌ Error: Cannot import pbd module"
    echo "Available modules in $ROOT_DIR:"
    ls -la "$ROOT_DIR"
    exit 1
}



# Run pipeline
cd "$PIPELINE_DIR"  # Change to pipeline directory first
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

echo "✅ Running Metaflow pipeline '$PIPELINE_NAME' with Kubernetes..."
echo "📍 Working directory: $(pwd)"
echo "📂 Root directory: $ROOT_DIR"
echo "🐍 Python path: $PYTHONPATH"
echo "----------------------------------------"

echo "----------------------------------------"

# Try different command variations
echo "🚀 Attempting pipeline execution..."


# Second try: with config parameter in different position
#echo "Trying: python pipelines.py --config-file config.json run --with kubernetes"
#PYTHONPATH="$ROOT_DIR:$PYTHONPATH" python pipelines.py --config-file config.json run --with kubernetes && exit 0

# Third try: Check if it's a custom config option
echo "Trying: python pipelines.py run --config config --with kubernetes"
PYTHONPATH="$ROOT_DIR:$PYTHONPATH" python pipelines.py --config config config.json run --with kubernetes && exit 0

echo "❌ All attempts failed"

EXIT_CODE=$?
echo "----------------------------------------"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Pipeline '$PIPELINE_NAME' completed successfully"
else
    echo "❌ Pipeline failed with exit code $EXIT_CODE"
fi

# Cleanup
deactivate
exit $EXIT_CODE
