#!/bin/bash

# Set strict mode
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to check if ZenML is installed
check_zenml() {
  if ! command_exists zenml; then
    echo "Error: ZenML is not installed. Please install it first."
    echo "You can install it using: pip install zenml"
    exit 1
  fi
}

# Function to check if minikube is running
check_minikube() {
  if ! command_exists minikube; then
    echo "Error: minikube is not installed. Please install it first."
    exit 1
  fi

  if ! minikube status | grep -q "Running"; then
    echo "Error: minikube is not running. Please start it with: minikube start"
    exit 1
  fi
}

# Function to check if a component exists
component_exists() {
  local component_type=$1
  local component_name=$2

  zenml $component_type list | grep -q "$component_name"
  return $?
}

# Function to check if Minio is accessible
check_minio() {
  if ! curl -s --connect-timeout 5 http://fsml-minio.info > /dev/null; then
    echo "Warning: Cannot connect to Minio at http://fsml-minio.info"
    echo "Please ensure Minio is running and accessible."
    read -p "Do you want to continue anyway? (y/N): " continue_anyway
    if [[ ! "$continue_anyway" =~ ^[Yy]$ ]]; then
      exit 1
    fi
  else
    echo "✓ Minio is accessible at http://fsml-minio.info"
  fi
}

# Function to verify component was created successfully
verify_component() {
  local component_type=$1
  local component_name=$2

  if ! component_exists "$component_type" "$component_name"; then
    echo "Error: Failed to create component '$component_name' of type '$component_type'."
    exit 1
  else
    echo "✓ Component '$component_name' of type '$component_type' was successfully created."
  fi
}

# Function to verify Minio store configuration
verify_minio_store() {
  echo "Verifying Minio store configuration..."

  if ! zenml artifact-store describe minio_store | grep -q "s3://zenml_bucket"; then
    echo "Error: Minio store configuration is incorrect. Path not properly set."
    exit 1
  fi

  if ! zenml artifact-store describe minio_store | grep -q "fsml-minio.info"; then
    echo "Error: Minio store configuration is incorrect. Endpoint not properly set."
    exit 1
  fi

  echo "✓ Minio store is properly configured."
}

# Function to verify Kubernetes orchestrator configuration
verify_kubernetes_orchestrator() {
  echo "Verifying Kubernetes orchestrator configuration..."

  if ! zenml orchestrator describe minikube_orchestrator | grep -q "kubernetes"; then
    echo "Error: Kubernetes orchestrator configuration is incorrect. Flavor not properly set."
    exit 1
  fi

  if ! zenml orchestrator describe minikube_orchestrator | grep -q "minikube"; then
    echo "Error: Kubernetes orchestrator configuration is incorrect. Context not properly set."
    exit 1
  fi

  echo "✓ Kubernetes orchestrator is properly configured."
}

# Function to find stacks using specific components
find_stack_with_components() {
  local orchestrator=$1
  local artifact_store=$2

  # Get all stacks
  local stacks=$(zenml stack list | grep -E "👉|orchestrator|artifact_store")

  local stack_name=""
  local has_orchestrator=false
  local has_artifact_store=false

  while IFS= read -r line; do
    if [[ "$line" == *"👉"* ]]; then
      stack_name=$(echo "$line" | awk '{print $2}')
      # Reset flags when a new stack starts
      has_orchestrator=false
      has_artifact_store=false
    elif [[ "$line" == *"orchestrator"* && "$line" == *"$orchestrator"* ]]; then
      has_orchestrator=true
    elif [[ "$line" == *"artifact_store"* && "$line" == *"$artifact_store"* ]]; then
      has_artifact_store=true
    fi

    # If both components are found for the current stack, print and return
    if [[ $has_orchestrator == true && $has_artifact_store == true ]]; then
      echo "$stack_name"
      return
    fi
  done <<< "$stacks"

  # If no matching stack is found, return an empty string
  echo ""
}



# Function to verify stack configuration
verify_stack() {
  local stack_name=$1
  echo "Verifying stack configuration..."

  if ! zenml stack describe "$stack_name" | grep -q "minikube_orchestrator"; then
    echo "Error: Stack configuration is incorrect. Orchestrator not properly set."
    exit 1
  fi

  if ! zenml stack describe "$stack_name" | grep -q "minio_store"; then
    echo "Error: Stack configuration is incorrect. Artifact store not properly set."
    exit 1
  fi

  echo "✓ Stack is properly configured."
}

# Main script starts here
echo "Starting ZenML setup script..."

# Check prerequisites
check_zenml
#check_minikube
#check_minio

# Check if components already exist
minio_exists=false
orchestrator_exists=false

if component_exists "artifact-store" "minio_store"; then
  echo "Minio store 'minio_store' already exists."
  minio_exists=true
  verify_minio_store
else
  echo "Registering Minio artifact store..."
  zenml artifact-store register minio_store \
    --flavor=s3 \
    --path=s3://zenml_bucket \
    --client_kwargs='{"endpoint_url": "http://fsml-minio.info", "region_name": "us-east-1", "use_ssl": false, "aws_access_key_id": "minio@1234", "aws_secret_access_key": "minio@local1234"}'

  verify_component "artifact-store" "minio_store"
  verify_minio_store
fi

if component_exists "orchestrator" "minikube_orchestrator"; then
  echo "Kubernetes orchestrator 'minikube_orchestrator' already exists."
  orchestrator_exists=true
  verify_kubernetes_orchestrator
else
  echo "Registering Kubernetes orchestrator..."
  zenml orchestrator register minikube_orchestrator --flavor=kubernetes --kubernetes_context="minikube"

  verify_component "orchestrator" "minikube_orchestrator"
  verify_kubernetes_orchestrator
fi

# Get the current active stack
current_stack=$(zenml stack list | grep "active" | awk '{print $1}')
echo "Current active stack: $current_stack"
echo "Minio exist: $minio_exists"
echo "Orchestrator exist: $orchestrator_exists"
# Find existing stack that uses both components
if [[ $minio_exists == true && $orchestrator_exists == true ]]; then
  echo "Checking for existing stack with both components..."
  existing_stack=$(find_stack_with_components "minikube_orchestrator" "minio_store")

  if [[ -n "$existing_stack" ]]; then
    echo "Found existing stack '$existing_stack' with both components."

    # Check if it's already active
    if [[ "$existing_stack" == "$current_stack" ]]; then
      echo "Stack '$existing_stack' is already active."
    else
      echo "Setting stack '$existing_stack' as active..."
      zenml stack set "$existing_stack"
      echo "✓ Stack '$existing_stack' is now active."
    fi

    verify_stack "$existing_stack"
  else
    echo "No existing stack found with both components. Creating new stack..."
    zenml stack register local_k8s -o minikube_orchestrator -a minio_store --set
    verify_stack "local_k8s"
    echo "✓ New stack 'local_k8s' created and set as active."
  fi
else
  echo "Registering new stack..."
  zenml stack register local_k8s -o minikube_orchestrator -a minio_store --set
  verify_stack "local_k8s"
  echo "✓ New stack 'local_k8s' created and set as active."
fi

echo "Setup completed successfully!"
echo "Active stack is now: $(zenml stack list | grep "active" | awk '{print $1}')"