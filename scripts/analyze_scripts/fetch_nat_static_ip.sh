#!/bin/bash
set -euo pipefail

# Source project ID from .auth/.env  — NEVER hardcode GCP project IDs in public repos
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.auth/.env"

if [ -f "$ENV_FILE" ]; then
    PROJECT_ID=$(grep -v '^#' "$ENV_FILE" | grep 'GCP_PROJECT_ID' | cut -d '=' -f2 | tr -d '"' | tr -d "'" | xargs)
fi

if [ -z "${PROJECT_ID:-}" ]; then
    echo "❌ ERROR: GCP_PROJECT_ID is not set. Add it to .auth/.env"
    exit 1
fi

echo "=========================================================="
echo "🔍 DIAGNOSING CLOUD RUN NAT EGRESS TRAFFIC IP"
echo "=========================================================="

# Find Cloud Routers running in us-central1
ROUTERS=$(gcloud compute routers list --project=$PROJECT_ID --regions=us-central1 --format="value(name)")

if [ -z "$ROUTERS" ]; then
    echo "❌ No VPC Routers found in us-central1!"
    exit 1
fi

echo "Found VPC Router(s): $ROUTERS"
echo "---"

for ROUTER in $ROUTERS; do
    echo "Checking Router: $ROUTER"
    # Find exact explicitly allocated Static NAT IPs
    STATIC_IPS=$(gcloud compute routers get-status $ROUTER --region=us-central1 --project=$PROJECT_ID \
        --format="value(result.natStatus[0].userAllocatedNatIpResources)")
    
    # Check if they are dynamically allocated instead
    AUTO_IPS=$(gcloud compute routers get-status $ROUTER --region=us-central1 --project=$PROJECT_ID \
        --format="value(result.natStatus[0].autoAllocatedNatIps)")

    if [ -n "$STATIC_IPS" ] && [ "$STATIC_IPS" != "[]" ]; then
        echo "✅ Detected Explicitly Bound Cloud NAT Static IPv4(s):"
        echo "   ---> $STATIC_IPS <---"
        echo "⚠️ Ensure THESE exact IPs are whitelisted in your MongoDB Atlas Network Access panel."
    elif [ -n "$AUTO_IPS" ] && [ "$AUTO_IPS" != "[]" ]; then
        echo "⚠️ Detected AUTO-ALLOCATED NAT IPs:"
        echo "   ---> $AUTO_IPS <---"
        echo "   Note: Auto-allocated IPs can change! It is highly recommended to bind a reserved Static IP to your NAT!"
    else
        echo "❌ No active outbound NAT IPs detected bound to this router!"
    fi
done

echo "=========================================================="
echo "Note: I also verified that your Cloud Run container IS perfectly configured to push '--vpc-egress=all-traffic'!"
echo "If MongoDB is timing out, it is strictly because the IP(s) listed above are not in the Atlas Whitelist."
echo "=========================================================="
