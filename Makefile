# --- Makefile for Agentic Personal Porter ---
SHELL := /bin/bash

# Variables
CONDA_ENV = agentic_porter
IMAGE_NAME = agentic-porter
PORT = 6010
PYTHON = python
PIP = pip

# Phony targets to prevent conflicts with file names
.PHONY: help install update run dev build-css docker-build docker-run docker-stop clean test pulse

help: ## Show this help message with available commands
	@echo "Agentic Personal Porter Management Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Environment Management ---
install: ## Create the conda environment and install all dependencies
	conda create -n $(CONDA_ENV) python=3.11 nodejs -y
	conda run -n $(CONDA_ENV) uv sync --dev

install-uv: ## Install dependencies using uv package manager
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source $HOME/.local/bin/env; }
	conda run -n $(CONDA_ENV) uv sync --dev

update: ## Update the conda environment from requirements.txt
	conda run -n $(CONDA_ENV) $(PIP) install -r requirements.txt

# --- Development & Execution ---
# Run unit and integration tests
dev: ## Start the backend in development mode (Flask server)
	@echo "Starting development server on port $(PORT)..."
	conda run -n $(CONDA_ENV) $(PYTHON) src/app.py

run: build-css ## Start the backend in production mode (Gunicorn)
	@echo "Starting production server on port $(PORT)..."
	conda run -n $(CONDA_ENV) gunicorn --bind 127.0.0.1:$(PORT) --workers 1 --threads 4 src.app:app

test: ## Run the test suite using pytest
	@test -n "$(GOOGLE_CLOUD_PROJECT)" || (echo "Error: GOOGLE_CLOUD_PROJECT is not set. Setup environment before running tests" && exit 1)
	DISABLE_CLOUD_LOGGING=true conda run -n $(CONDA_ENV) pytest tests/
# Run code quality checks (codespell, ruff, mypy)
lint:
	@echo "Running code quality checks..."
	conda run -n $(CONDA_ENV) uv sync --dev
	conda run -n $(CONDA_ENV) uv run codespell -s
	conda run -n $(CONDA_ENV) uv run ruff check . --diff
	conda run -n $(CONDA_ENV) uv run mypy .

pulse: ## Execute the local system health diagnostic
	conda run -n $(CONDA_ENV) python helper_scripts/local_pulse_check.py

# --- Frontend Assets ---
build-css: ## Build and minify Tailwind CSS assets
	@echo "Building CSS assets..."
	npm run build:css

# --- Docker Operations ---
docker-build: ## Build the production Docker image
	@echo "Building Docker image: $(IMAGE_NAME)..."
	docker build -t $(IMAGE_NAME) .

docker-run: ## Run the Docker container locally (requires .auth/.env)
	@echo "Launching container on port $(PORT)..."
	docker run -p $(PORT):$(PORT) --env-file .auth/.env -v $(PWD)/.auth:/app/.auth -v $(PWD)/data:/app/data -v ~/.config/gcloud:/root/.config/gcloud:ro $(IMAGE_NAME)

docker-stop: ## Stop any running containers for this project
	@echo "Stopping $(IMAGE_NAME) containers..."
	docker stop $$(docker ps -q --filter ancestor=$(IMAGE_NAME)) 2>/dev/null || true

# Deploy the Cloud Run Function
deploy:
	@if [ ! -f .auth/.env ]; then echo "Error: .env file not found."; exit 1; fi
	@source .auth/.env && \
	export SERVICE_ACCOUNT_NAME="$$FUNCTION_NAME-sa" && \
	export SERVICE_ACCOUNT_EMAIL="$$SERVICE_ACCOUNT_NAME@$$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com" && \
	gcloud run deploy $$FUNCTION_NAME \
	  --base-image=python312 \
	  --project=$$GOOGLE_CLOUD_PROJECT \
	  --region=$$GOOGLE_CLOUD_REGION \
	  --source=./src/infrastructure/billing_killswitch/ \
	  --function=disable_billing_for_projects \
	  --no-allow-unauthenticated \
	  --execution-environment=gen1 \
	  --cpu=0.2 \
	  --memory=256Mi \
	  --concurrency=1 \
	  --min-instances=0 \
	  --max-instances=1 \
	  --service-account="$$SERVICE_ACCOUNT_EMAIL" \
	  --set-env-vars LOG_LEVEL=$$LOG_LEVEL,SIMULATE_DEACTIVATION=$$SIMULATE_DEACTIVATION

# --- Maintenance & Cleanup ---
clean: ## Remove temporary files and archive backups to .legacy_hr
	@echo "Archiving .bk files to .legacy_hr..."
	@mkdir -p .legacy_hr
	@find . -maxdepth 2 -name "*.bk" -exec mv {} .legacy_hr/ \;
	@echo "Cleaning Python cache files..."
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -delete
	@echo "Cleanup complete."
