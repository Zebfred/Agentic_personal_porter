# Use the official Python base image
FROM python:3.11-slim as builder

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies in the builder stage
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

# --- Production Stage ---
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files (ignoring items in .dockerignore)
COPY src/ ./src/
COPY frontend/ ./frontend/

# Create data directory structure for CrewAI artifacts and logs
RUN mkdir -p /app/data/reflections

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Expose the Flask Port
EXPOSE 5090

# Health check to ensure the server is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5090/ || exit 1

# Start the application using Gunicorn (WSGI)
CMD ["gunicorn", "--bind", "0.0.0.0:5090", "--workers", "1", "--threads", "4", "src.app:app"]
