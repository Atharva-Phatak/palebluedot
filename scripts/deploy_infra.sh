#!/bin/bash

# Set strict mode
set -euo pipefail

# Usage check
if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <deploy|destroy> <stack-name>"
    exit 1
fi

COMMAND="$1"
STACK="$2"

# Load .env secrets
set -o allexport
. .env
set +o allexport

echo "✅ Loaded secrets from .env"

# Paths
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INFRA_PATH="$ROOT_DIR/infra"
VENV_PATH="${INFRA_PATH}/.venv"

echo "📁 Venv path: $VENV_PATH"
echo "----------------------------------------"

# Activate virtualenv
cd "$ROOT_DIR"
source "$VENV_PATH/bin/activate"

# Move to Pulumi project
cd "$INFRA_PATH"

# Handle command
case "$COMMAND" in
    deploy)
        # Create stack if it doesn't exist
        if ! pulumi stack select "$STACK" 2>/dev/null; then
            echo "🆕 Stack '$STACK' not found. Creating it..."
            pulumi stack init "$STACK"
        fi
        echo "🚀 Deploying stack '$STACK'..."
        pulumi up --yes --stack "$STACK"
        ;;
    destroy)
        if pulumi stack select "$STACK" 2>/dev/null; then
            echo "🔥 Destroying stack '$STACK'..."
            pulumi destroy --yes --stack "$STACK"
            echo "🗑️ Removing stack '$STACK'..."
            pulumi stack rm --yes "$STACK"
        else
            echo "⚠️ Stack '$STACK' does not exist."
        fi
        ;;
    *)
        echo "❌ Invalid command: $COMMAND. Use 'deploy' or 'destroy'."
        exit 1
        ;;
esac
