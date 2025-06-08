#!/bin/bash
# Set strict mode
set -euo pipefail

# Load secrets from .env
set -o allexport
if [ -f .env ]; then
    . .env
    echo "🔐 Environment variables loaded from .env"
else
    echo "⚠️  No .env file found, using existing environment variables"
fi
set +o allexport

# Helper function to check if a component exists
check_component_exists() {
    local component_type="$1"
    local component_name="$2"
    
    case "$component_type" in
        "secret")
            zenml secret list 2>&1 | grep -F "$component_name" >/dev/null
            ;;
        "artifact-store")
            zenml artifact-store list 2>&1 | grep -F "$component_name" >/dev/null
            ;;
        "orchestrator")
            zenml orchestrator list 2>&1 | grep -F "$component_name" >/dev/null
            ;;
        "container-registry")
            zenml container-registry list 2>&1 | grep -F "$component_name" >/dev/null
            ;;
        "code-repository")
            zenml code-repository list 2>&1 | grep -F "$component_name" >/dev/null
            ;;
        "stack")
            zenml stack list 2>&1 | grep -F "$component_name" >/dev/null
            ;;
        "alerter")
            zenml alerter list 2>&1 | grep -F "$component_name" >/dev/null
            ;;
        *)
            return 1
    esac
}

# 1. Register secret if it doesn't exist
echo "🔐 Checking GitHub secret..."
if check_component_exists "secret" "github_secret"; then
    echo "✅ GitHub secret already exists. Skipping..."
else
    echo "🔐 Registering GitHub secret..."
    if [ -z "${GITHUB_TOKEN:-}" ]; then
        echo "❌ Error: GITHUB_TOKEN environment variable is not set"
        exit 1
    fi
    zenml secret create github_secret --pa_token="$GITHUB_TOKEN"
fi

echo "🔐 Checking Slack secret..."
if check_component_exists "secret" "slack_secret"; then
    echo "✅ Slack secret already exists. Skipping..."
else
    echo "🔐 Registering Slack secret..."
    if [ -z "${SLACK_TOKEN:-}" ]; then
        echo "❌ Error: SLACK_TOKEN environment variable is not set"
        exit 1
    fi
    zenml secret create slack_secret --pa_token="$SLACK_TOKEN"
fi

# 2. Register artifact store
echo "🪣 Checking Minio artifact store..."
if check_component_exists "artifact-store" "minio_store"; then
    echo "✅ Artifact store 'minio_store' already exists. Skipping..."
else
    echo "🪣 Registering Minio artifact store..."
    zenml artifact-store register minio_store \
        --flavor=s3 \
        --path=s3://zenml-bucket \
        --client_kwargs='{"endpoint_url": "http://fsml-minio.info", "region_name": "us-east-1"}'
fi

# 3. Register orchestrator
echo "⚙️ Checking Kubernetes orchestrator..."
if check_component_exists "orchestrator" "minikube_orchestrator"; then
    echo "✅ Orchestrator 'minikube_orchestrator' already exists. Skipping..."
else
    echo "⚙️ Registering Kubernetes orchestrator..."
    zenml orchestrator register minikube_orchestrator \
        --flavor=kubernetes \
        --kubernetes_context="minikube"
fi

# 4. Register container registry
echo "📦 Checking container registry..."
if check_component_exists "container-registry" "ghcr"; then
    echo "✅ Container registry 'ghcr' already exists. Skipping..."
else
    echo "📦 Registering container registry..."
    zenml container-registry register ghcr \
        --flavor=github \
        --uri=ghcr.io/atharva-phatak
fi

# 5. Register code repository
echo "📁 Checking code repository..."
if check_component_exists "code-repository" "palebluedot"; then
    echo "✅ Code repository 'palebluedot' already exists. Skipping..."
else
    echo "📁 Registering code repository..."
    zenml code-repository register palebluedot \
        --type=github \
        --owner=Atharva-Phatak \
        --repository=palebluedot \
        --token={{github_secret.pa_token}}
fi


# 7. Register slack alerter
echo "🚨 Checking Slack alerter..."
if check_component_exists "alerter" "slack_alerter"; then
    echo "✅ Alerter 'slack_alerter' already exists. Skipping..."
else
    echo "🚨 Registering Slack alerter..."
    if [ -z "${SLACK_CHANNEL_ID:-}" ]; then
        echo "❌ Error: SLACK_CHANNEL_ID environment variable is not set"
        exit 1
    fi
    zenml alerter register slack_alerter \
        --flavor=slack \
        --slack_token={{slack_secret.pa_token}} \
        --slack_channel_id="$SLACK_CHANNEL_ID"
fi

# 6. Register and set active stack
echo "🔧 Checking stack configuration..."
if check_component_exists "stack" "k8s_stack"; then
    echo "✅ Stack 'k8s_stack' already exists. Setting it as active..."
    zenml stack set k8s_stack
else
    echo "🔧 Registering stack 'k8s_stack'..."
    zenml stack register k8s_stack \
        -o minikube_orchestrator \
        -a minio_store \
        -c ghcr \
        -al slack_alerter \
        --set
fi



echo "🎉 ZenML setup completed successfully!"
echo "📊 Current active stack:"
zenml stack describe