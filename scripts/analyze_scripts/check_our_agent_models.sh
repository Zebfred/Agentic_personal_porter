#!/bin/bash

# Ensure we're running from the project root or adjust path accordingly
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call the python checker script using the correct conda environment
uv run python "$SCRIPT_DIR/check_our_agent_models.py"
