# --- Makefile for Agentic Personal Porter ---

# Variables
CONDA_ENV = pp_env
IMAGE_NAME = agentic-porter
PORT = 5090
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
	conda create -n $(CONDA_ENV) python=3.11 -y
	conda run -n $(CONDA_ENV) $(PIP) install -r requirements.txt
	conda run -n $(CONDA_ENV) $(PIP) install gunicorn

update: ## Update the conda environment from requirements.txt
	conda run -n $(CONDA_ENV) $(PIP) install -r requirements.txt

# --- Development & Execution ---
dev: ## Start the backend in development mode (Flask server)
	@echo "Starting development server on port $(PORT)..."
	conda run -n $(CONDA_ENV) $(PYTHON) src/app.py

run: build-css ## Start the backend in production mode (Gunicorn)
	@echo "Starting production server on port $(PORT)..."
	conda run -n $(CONDA_ENV) gunicorn --bind 0.0.0.0:$(PORT) --workers 1 --threads 4 src.app:app

test: ## Run the test suite using pytest
	conda run -n $(CONDA_ENV) pytest tests/

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
	docker run -p $(PORT):$(PORT) --env-file .auth/.env $(IMAGE_NAME)

docker-stop: ## Stop any running containers for this project
	@echo "Stopping $(IMAGE_NAME) containers..."
	docker stop $$(docker ps -q --filter ancestor=$(IMAGE_NAME)) 2>/dev/null || true

# --- Maintenance & Cleanup ---
clean: ## Remove temporary files and archive backups to .legacy_hr
	@echo "Archiving .bk files to .legacy_hr..."
	@mkdir -p .legacy_hr
	@find . -maxdepth 2 -name "*.bk" -exec mv {} .legacy_hr/ \;
	@echo "Cleaning Python cache files..."
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -delete
	@echo "Cleanup complete."
