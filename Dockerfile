# Use the official Python base image
FROM python:3.12-slim AS builder

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (creates /app/.venv)
RUN uv sync --frozen --no-cache --no-install-project --no-dev

# --- Production Stage ---
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Prepend the venv to PATH so Python uses the installed dependencies
ENV PATH="/app/.venv/bin:$PATH"

# Run the ABI mismatch check using the venv's python
RUN /app/.venv/bin/python -c "import torch; import onnxruntime" 

# Copy application files (ignoring items in .dockerignore)
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY data/category_mapping.example.json ./data/

# Create data directory structure for Agent artifacts and logs
RUN mkdir -p /app/data/reflections

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Expose the Flask Port
EXPOSE 6010

# Health check to ensure the server is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:6010/ || exit 1

# Start the application using Gunicorn (WSGI)
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-6010} --workers 1 --threads 4 --timeout 300 src.app:app"]
