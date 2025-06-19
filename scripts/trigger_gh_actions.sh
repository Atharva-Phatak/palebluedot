#!/bin/bash

# PaleBlueDot GitHub Pipeline Trigger Script
# Repository: https://github.com/Atharva-Phatak/palebluedot
# Usage: ./trigger_palebluedot_pipeline.sh [options]

set -e

# Load .env secrets
set -o allexport
. .env
set +o allexport

echo "✅ Loaded secrets from .env"

# Repository Configuration
GITHUB_OWNER="Atharva-Phatak"
GITHUB_REPO="palebluedot"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Common workflow files (update these based on your actual workflows)
AVAILABLE_WORKFLOWS=(
  "docker_build_push.yaml"
)

# Default values
DEFAULT_WORKFLOW="docker_build_push.yaml"
DEFAULT_BRANCH="main"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                    PaleBlueDot Pipeline Trigger              ║${NC}"
    echo -e "${PURPLE}║                 Repository: Atharva-Phatak/palebluedot       ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to show usage
show_usage() {
    print_header
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -w, --workflow FILE    Workflow file name (default: ${DEFAULT_WORKFLOW})"
    echo "  -b, --branch BRANCH    Branch to run workflow on (default: ${DEFAULT_BRANCH})"
    echo "  -i, --inputs JSON      Workflow inputs as JSON string"
    echo "  -t, --token TOKEN      GitHub personal access token"
    echo "  -l, --list             List available workflows"
    echo "  -s, --status           Show recent workflow runs"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GITHUB_TOKEN           GitHub personal access token (required)"
    echo ""
    echo "Common Workflows (update based on your actual workflows):"
    for workflow in "${AVAILABLE_WORKFLOWS[@]}"; do
        echo "  - $workflow"
    done
    echo ""
    echo "Examples:"
    echo "  # Basic trigger with default workflow"
    echo "  $0"
    echo ""
    echo "  # Trigger specific workflow"
    echo "  $0 -w build.yml"
    echo ""
    echo "  # Trigger on specific branch"
    echo "  $0 -w deploy.yml -b production"
    echo ""
    echo "  # Trigger with inputs"
    echo "  $0 -w deploy.yml -i '{\"environment\":\"staging\",\"version\":\"1.0.0\"}'"
    echo ""
    echo "  # List available workflows"
    echo "  $0 -l"
    echo ""
    echo "  # Check workflow status"
    echo "  $0 -s"
    echo ""
    echo "Setup:"
    echo "  1. Create a GitHub Personal Access Token with 'repo' and 'actions:write' permissions"
    echo "  2. Set the token: export GITHUB_TOKEN='your_token_here'"
    echo "  3. Update AVAILABLE_WORKFLOWS array with your actual workflow files"
}

# Function to validate required parameters
validate_params() {
    if [[ -z "$GITHUB_TOKEN" ]]; then
        print_error "GitHub token is required!"
        echo ""
        echo "Please set your GitHub token:"
        echo "  export GITHUB_TOKEN='your_token_here'"
        echo ""
        echo "To create a token:"
        echo "  1. Go to GitHub Settings → Developer settings → Personal access tokens"
        echo "  2. Generate new token with 'repo' and 'actions:write' permissions"
        echo "  3. Copy the token and set it as environment variable"
        exit 1
    fi
}

# Function to check if workflow exists
check_workflow_exists() {
    local workflow="$1"

    print_step "Checking if workflow '$workflow' exists..."

    local api_url="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${workflow}"

    local response=$(curl -s -w "%{http_code}" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        "$api_url")

    local http_code="${response: -3}"

    if [[ "$http_code" == "200" ]]; then
        print_success "Workflow '$workflow' found!"
        return 0
    else
        print_error "Workflow '$workflow' not found!"
        print_warning "Available workflows might be different. Use -l to list actual workflows."
        return 1
    fi
}

# Function to trigger workflow
trigger_workflow() {
    local workflow="$1"
    local branch="$2"
    local inputs="$3"

    print_header
    print_step "Preparing to trigger workflow..."

    local api_url="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${workflow}/dispatches"

    print_info "Repository: ${GITHUB_OWNER}/${GITHUB_REPO}"
    print_info "Workflow: ${workflow}"
    print_info "Branch: ${branch}"

    if [[ -n "$inputs" ]]; then
        print_info "Inputs: ${inputs}"
    fi

    # Check if workflow exists first
    if ! check_workflow_exists "$workflow"; then
        exit 1
    fi

    # Prepare the payload
    local payload="{\"ref\":\"${branch}\""

    if [[ -n "$inputs" ]]; then
        payload="${payload},\"inputs\":${inputs}"
    fi

    payload="${payload}}"

    print_step "Sending request to GitHub API..."

    # Make the API call
    local response=$(curl -s -w "%{http_code}" \
        -X POST \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$api_url")

    local http_code="${response: -3}"
    local response_body="${response%???}"

    echo ""
    if [[ "$http_code" == "204" ]]; then
        print_success "🚀 Workflow triggered successfully!"
        echo ""
        print_info "Next steps:"
        echo "  1. Check the Actions tab: https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/actions"
        echo "  2. Look for the latest workflow run"
        echo "  3. Monitor the progress and logs"
        echo ""
        print_info "You can also check status with: $0 -s"
    else
        print_error "❌ Failed to trigger workflow!"
        print_error "HTTP Code: ${http_code}"
        if [[ -n "$response_body" ]]; then
            print_error "Response: ${response_body}"
        fi
        echo ""
        print_warning "Common issues:"
        echo "  - Workflow file doesn't exist or has wrong name"
        echo "  - Branch doesn't exist"
        echo "  - Insufficient permissions on GitHub token"
        echo "  - Repository is private and token doesn't have access"
        exit 1
    fi
}

# Function to list available workflows
list_workflows() {
    print_header
    print_step "Fetching workflows from GitHub..."

    local api_url="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows"

    local response=$(curl -s -w "%{http_code}" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        "$api_url")

    local http_code="${response: -3}"
    local response_body="${response%???}"

    if [[ "$http_code" == "200" ]]; then
        print_success "Available workflows:"
        echo ""
        echo "$response_body" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | while read -r workflow; do
            echo "  📄 $workflow"
        done
        echo ""
        print_info "Use any of these workflow names with the -w option"
    else
        print_error "Failed to fetch workflows. HTTP Code: ${http_code}"
        if [[ -n "$response_body" ]]; then
            print_error "Response: ${response_body}"
        fi
    fi
}

# Function to show workflow status
show_workflow_status() {
    print_header
    print_step "Fetching recent workflow runs..."

    local api_url="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/runs?per_page=5"

    local response=$(curl -s -w "%{http_code}" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        "$api_url")

    local http_code="${response: -3}"
    local response_body="${response%???}"

    if [[ "$http_code" == "200" ]]; then
        print_success "Recent workflow runs:"
        echo ""
        # Parse and display recent runs (simplified)
        echo "$response_body" | grep -E '"name"|"status"|"conclusion"|"created_at"' | \
        paste - - - - | \
        head -5 | \
        while IFS=$'\t' read -r name status conclusion created; do
            name=$(echo "$name" | sed 's/.*"name":"//g' | sed 's/",.*//g')
            status=$(echo "$status" | sed 's/.*"status":"//g' | sed 's/",.*//g')
            conclusion=$(echo "$conclusion" | sed 's/.*"conclusion":"//g' | sed 's/",.*//g')
            created=$(echo "$created" | sed 's/.*"created_at":"//g' | sed 's/",.*//g')

            echo "  🔄 $name | Status: $status | Result: $conclusion | Created: $created"
        done
        echo ""
        print_info "View all runs: https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/actions"
    else
        print_error "Failed to fetch workflow runs. HTTP Code: ${http_code}"
    fi
}

# Parse command line arguments
WORKFLOW="$DEFAULT_WORKFLOW"
BRANCH="$DEFAULT_BRANCH"
INPUTS=""
LIST_WORKFLOWS=false
SHOW_STATUS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -w|--workflow)
            WORKFLOW="$2"
            shift 2
            ;;
        -b|--branch)
            BRANCH="$2"
            shift 2
            ;;
        -i|--inputs)
            INPUTS="$2"
            shift 2
            ;;
        -t|--token)
            GITHUB_TOKEN="$2"
            shift 2
            ;;
        -l|--list)
            LIST_WORKFLOWS=true
            shift
            ;;
        -s|--status)
            SHOW_STATUS=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
done

# Validate required parameters
validate_params

# Execute requested action
if [[ "$LIST_WORKFLOWS" == "true" ]]; then
    list_workflows
elif [[ "$SHOW_STATUS" == "true" ]]; then
    show_workflow_status
else
    trigger_workflow "$WORKFLOW" "$BRANCH" "$INPUTS"
fi