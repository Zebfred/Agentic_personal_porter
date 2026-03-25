#!/bin/bash
# Production server script for Agentic Personal Porter

echo "Starting Agentic Personal Porter using Gunicorn WSGI Server..."

# Number of workers is typically CPUs * 2 + 1
# We are currently defaulting to 1 worker + 4 threads to resemble Dockerfile container setup.
gunicorn --bind 0.0.0.0:5090 --workers 1 --threads 4 src.app:app
