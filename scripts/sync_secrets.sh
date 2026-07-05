#!/usr/bin/env bash
#
# sync_secrets.sh
# Syncs secrets from GCP Secret Manager and Cloud SQL private IP into Kubernetes base Secrets manifest.
#

set -euo pipefail

# Default values
PROJECT_ID="clean-carrier-500104-i0"
ENVIRONMENT=""

# Help/Usage function
usage() {
    cat <<EOF
Usage: $(basename "$0") -e <environment> [-p <project_id>]

Options:
  -e, --environment     Deployment environment: staging or prod (Required)
  -p, --project         GCP Project ID (Default: clean-carrier-500104-i0)
  -h, --help            Show this help message and exit

Description:
  This script fetches secrets from Google Cloud Secret Manager and constructs the
  PostgreSQL DSN by querying the Cloud SQL instance IP. It base64 encodes the
  secrets and writes them to 'infra/k8s/base/secrets.yaml'.

  If 'gcloud' is not available, you can populate the following environment variables:
    GEMINI_API_KEY, JWT_SECRET_KEY, DB_PASSWORD, DEFAULT_API_KEY, DB_IP
  to bypass GCP Secret Manager queries.
EOF
}

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

# Validate environment
if [[ -z "${ENVIRONMENT}" ]]; then
    echo "Error: Environment (-e/--environment) is required." >&2
    usage >&2
    exit 1
fi

if [[ "${ENVIRONMENT}" != "staging" && "${ENVIRONMENT}" != "prod" ]]; then
    echo "Error: Environment must be 'staging' or 'prod'." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="${SCRIPT_DIR}/../infra/k8s/base/secrets.yaml"

# Disable interactive prompts in gcloud commands (non-interactive mode)
export CLOUDSDK_CORE_DISABLE_PROMPTS=1

# Check if gcloud is installed
HAS_GCLOUD=true
if ! command -v gcloud &> /dev/null; then
    HAS_GCLOUD=false
    echo "gcloud CLI not found in PATH."
fi

# Check if we should use GCP or fallback to env variables
USE_GCP=true
if [ "$HAS_GCLOUD" = false ]; then
    USE_GCP=false
elif [ -n "${GEMINI_API_KEY:-}" ] && [ -n "${JWT_SECRET_KEY:-}" ] && [ -n "${DB_PASSWORD:-}" ] && [ -n "${DEFAULT_API_KEY:-}" ] && [ -n "${DB_IP:-}" ]; then
    echo "Bypassing GCP Secret Manager because all required environment variables are already set in your terminal."
    USE_GCP=false
fi

# Fetch from GCP Secret Manager or check Env Variables fallback
if [ "$USE_GCP" = true ]; then
    echo "Fetching secrets from GCP Secret Manager in project: ${PROJECT_ID}..."
    
    # Helper to fetch a secret and print its value, or display stderr and exit on failure
    fetch_secret() {
        local secret_name="$1"
        local val
        local err_file
        err_file=$(mktemp)
        
        if val=$(gcloud secrets versions access latest --secret="$secret_name" --project="${PROJECT_ID}" 2>"$err_file"); then
            echo -n "$val"
            rm -f "$err_file"
        else
            echo ""
            echo "Error: Failed to fetch secret '$secret_name' from project '${PROJECT_ID}'." >&2
            echo "gcloud CLI Error details:" >&2
            cat "$err_file" >&2
            rm -f "$err_file"
            exit 1
        fi
    }

    GEMINI_API_KEY=$(fetch_secret "ekc-gemini-api-key")
    JWT_SECRET_KEY=$(fetch_secret "ekc-jwt-secret-key")
    DB_PASSWORD=$(fetch_secret "ekc-postgres-password")
    DEFAULT_API_KEY=$(fetch_secret "ekc-default-api-key")

    echo "Querying Cloud SQL instance for private IP..."
    # The Cloud SQL instance name: ekc-db-<environment>
    err_file=$(mktemp)
    if ! DB_IP=$(gcloud sql instances describe "ekc-db-${ENVIRONMENT}" \
        --project="${PROJECT_ID}" \
        --format="value(ipAddresses.where(type:PRIVATE).ipAddress)" 2>"$err_file"); then
        
        # Attempt fallback to any IP address
        if ! DB_IP=$(gcloud sql instances describe "ekc-db-${ENVIRONMENT}" \
            --project="${PROJECT_ID}" \
            --format="value(ipAddresses[0].ipAddress)" 2>"$err_file"); then
            echo "Error: Failed to fetch IP for Cloud SQL instance 'ekc-db-${ENVIRONMENT}' in project '${PROJECT_ID}'." >&2
            echo "gcloud CLI Error details:" >&2
            cat "$err_file" >&2
            rm -f "$err_file"
            exit 1
        fi
    fi
    rm -f "$err_file"

    if [ -z "${DB_IP:-}" ]; then
        echo "Error: Could not retrieve DB IP address (value is empty)." >&2
        exit 1
    fi
else
    # Fallback checks
    echo "Running in offline/fallback mode. Checking environment variables..."
    
    REQUIRED_VARS=(GEMINI_API_KEY JWT_SECRET_KEY DB_PASSWORD DEFAULT_API_KEY DB_IP)
    MISSING_VARS=()
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var:-}" ]; then
            MISSING_VARS+=("$var")
        fi
    done

    if [ ${#MISSING_VARS[@]} -ne 0 ]; then
        echo "Error: gcloud is missing and the following required env variables are not set:" >&2
        for var in "${MISSING_VARS[@]}"; do
            echo "  - $var" >&2
        done
        exit 1
    fi
fi

# Build POSTGRES_DSN
POSTGRES_DSN="postgresql://knowledge_copilot_user:${DB_PASSWORD}@${DB_IP}:5432/knowledge_copilot"

# Base64 encode function (handles newlines cleanly across OS distributions)
encode_base64() {
    echo -n "$1" | base64 | tr -d '\n\r'
}

GEMINI_API_KEY_B64=$(encode_base64 "$GEMINI_API_KEY")
JWT_SECRET_KEY_B64=$(encode_base64 "$JWT_SECRET_KEY")
POSTGRES_DSN_B64=$(encode_base64 "$POSTGRES_DSN")
DEFAULT_API_KEY_B64=$(encode_base64 "$DEFAULT_API_KEY")

echo "Updating secrets manifest: ${SECRETS_FILE}"

# Write to secrets file
cat <<EOF > "${SECRETS_FILE}"
apiVersion: v1
kind: Secret
metadata:
  name: ekc-secrets
type: Opaque
data:
  GEMINI_API_KEY: "${GEMINI_API_KEY_B64}"
  JWT_SECRET_KEY: "${JWT_SECRET_KEY_B64}"
  POSTGRES_DSN: "${POSTGRES_DSN_B64}"
  DEFAULT_API_KEY: "${DEFAULT_API_KEY_B64}"
EOF

echo "Successfully updated secrets file for ${ENVIRONMENT}."
echo "WARNING: ${SECRETS_FILE} now contains base64 encoded credentials. Do NOT commit this file to Git."
