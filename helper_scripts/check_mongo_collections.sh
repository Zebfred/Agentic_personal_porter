#!/bin/bash
# Helper script to review all MongoDB collections for the Agentic Personal Porter

# Get absolute path to the directory containing this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "Activating agentic_porter environment and gathering MongoDB statistics..."
echo "======================================================================="
conda run -n agentic_porter python "$SCRIPT_DIR/mongo_collections_overview.py"
