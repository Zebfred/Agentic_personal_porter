#!/bin/bash
set -euo pipefail

# Production server script for Agentic Personal Porter

echo "Starting Agentic Personal Porter using Gunicorn WSGI Server..."

# Initialize conda so we can activate the environment
if [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
else
    echo "ERROR: conda initialization script not found. Please ensure conda is installed." >&2
    exit 1
fi

conda activate pp_env

# Check if gunicorn is available in the environment
if ! command -v gunicorn &> /dev/null; then
    echo "ERROR: gunicorn not found in the pp_env environment. Please ensure requirements are installed." >&2
    exit 1
fi

# Number of workers is typically CPUs * 2 + 1
# We are currently defaulting to 1 worker + 4 threads to resemble Dockerfile container setup.
gunicorn --bind 0.0.0.0:6010 --workers 1 --threads 4 src.app:app
