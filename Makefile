# --- Makefile for Agentic Personal Porter ---
# Cross-platform SHELL detection: use bash on Unix, cmd on Windows
ifeq ($(OS),Windows_NT)
    SHELL := cmd.exe
else
    SHELL := /bin/bash
endif

# Variables
CONDA_ENV = agentic_porter
IMAGE_NAME = agentic-porter
PORT = 6010
PYTHON = uv run python
PIP = pip

# Platform detection
ifeq ($(OS),Windows_NT)
    GCLOUD_CONFIG_DIR := $(subst \,/,$(APPDATA))/gcloud
else
    GCLOUD_CONFIG_DIR := ~/.config/gcloud
endif

# Phony targets to prevent conflicts with file names
.PHONY: help install update run dev build-css docker-build docker-run docker-stop clean test pulse sync-brain ingest-private-brain trace-lineage

help: ## Show this help message with available commands
ifeq ($(OS),Windows_NT)
	@echo Agentic Personal Porter Management Commands:
	@echo.
	@powershell -Command "Get-Content $(MAKEFILE_LIST) | Select-String '^[a-zA-Z_-]+:.*?## ' | ForEach-Object { $$_ -match '^([a-zA-Z_-]+):.*?## (.*)$$' | Out-Null; Write-Host ('{0,-20} {1}' -f $$Matches[1], $$Matches[2]) }"
else
	@echo "Agentic Personal Porter Management Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
endif

# --- Environment Management ---
install: ## Create the conda environment and install all dependencies
	conda create -n $(CONDA_ENV) python=3.12 nodejs -y
	conda run -n $(CONDA_ENV) uv sync --dev

install-uv: ## Install dependencies using uv package manager
ifeq ($(OS),Windows_NT)
	@powershell -Command "if (!(Get-Command uv -ErrorAction SilentlyContinue)) { Write-Host 'uv is not installed. Installing uv...'; Invoke-RestMethod https://astral.sh/uv/0.6.12/install.ps1 | Invoke-Expression }"
	conda run -n $(CONDA_ENV) uv sync --dev
else
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source $HOME/.local/bin/env; }
	conda run -n $(CONDA_ENV) uv sync --dev
endif

update: ## Update the conda environment dependencies using uv sync
	conda run -n $(CONDA_ENV) uv sync --dev

# --- Development & Execution ---
# Run unit and integration tests
dev: ## Start the backend in development mode (Flask server)
	@echo "Starting development server on port $(PORT)..."
	conda run -n $(CONDA_ENV) $(PYTHON) src/app.py

run: build-css ## Start the backend in production mode (Gunicorn)
	@echo "Starting production server on port $(PORT)..."
	conda run -n $(CONDA_ENV) $(PYTHON) -m gunicorn --bind 127.0.0.1:$(PORT) --workers 1 --threads 4 src.app:app

test: ## Run the test suite using pytest
ifeq ($(OS),Windows_NT)
	@powershell -Command "\
		$$proj_id = '$$env:PROJECT_ID'; \
		if (!$$proj_id -and (Test-Path .auth/.env)) { \
			$$line = Get-Content .auth/.env | Select-String '^PROJECT_ID='; \
			if ($$line) { $$proj_id = ($$line -split '=', 2)[1] } \
		} \
		if (!$$proj_id) { \
			Write-Error 'Error: PROJECT_ID is not set in environment or .auth/.env.'; \
			exit 1; \
		} \
		$$env:PROJECT_ID = $$proj_id; \
		$$env:DISABLE_CLOUD_LOGGING = 'true'; \
		conda run -n $(CONDA_ENV) uv run pytest tests/ \
	"
else
	@proj_id="$(PROJECT_ID)"; \
	if [ -z "$$proj_id" ] && [ -f .auth/.env ]; then \
		proj_id=$$(grep -E '^PROJECT_ID=' .auth/.env | cut -d'=' -f2-); \
	fi; \
	if [ -z "$$proj_id" ]; then \
		echo "Error: PROJECT_ID is not set in environment or .auth/.env. Setup environment before running tests"; \
		exit 1; \
	fi; \
	PROJECT_ID="$$proj_id" DISABLE_CLOUD_LOGGING=true conda run -n $(CONDA_ENV) uv run pytest tests/
endif
# Run code quality checks (codespell, ruff, mypy)
lint:
	@echo "Running code quality checks..."
	conda run -n $(CONDA_ENV) uv sync --dev
	conda run -n $(CONDA_ENV) uv run codespell -s
	conda run -n $(CONDA_ENV) uv run ruff check . --diff
	conda run -n $(CONDA_ENV) uv run mypy .

pulse: ## Execute the local system health diagnostic
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$env:PYTHONPATH='.'; conda run -n $(CONDA_ENV) $(PYTHON) scripts/analyze_scripts/local_pulse_check.py"
else
	PYTHONPATH=. conda run -n $(CONDA_ENV) $(PYTHON) scripts/analyze_scripts/local_pulse_check.py
endif

trace-lineage: ## Trace a correlation ID across all data sources (Mongo, Neo4j, ChromaDB)
ifeq ($(OS),Windows_NT)
	@powershell -Command "\
		$$env:PYTHONPATH='.'; \
		if ('$(ID)' -eq '') { \
			conda run -n $(CONDA_ENV) $(PYTHON) scripts/analyze_scripts/trace_lineage.py --list \
		} else { \
			conda run -n $(CONDA_ENV) $(PYTHON) scripts/analyze_scripts/trace_lineage.py $(ID) \
		} \
	"
else
	@if [ -z "$(ID)" ]; then \
		PYTHONPATH=. conda run -n $(CONDA_ENV) $(PYTHON) scripts/analyze_scripts/trace_lineage.py --list; \
	else \
		PYTHONPATH=. conda run -n $(CONDA_ENV) $(PYTHON) scripts/analyze_scripts/trace_lineage.py $(ID); \
	fi
endif

sync-brain: ## Automate committing and pushing updates to the Agentic_Private_Brain submodule
ifeq ($(OS),Windows_NT)
	@powershell -ExecutionPolicy Bypass -File Agentic_Private_Brain/deployment_scripts/sync_brain.ps1
else
	@./Agentic_Private_Brain/deployment_scripts/sync_brain.sh
endif

ingest-private-brain: ## Parse the Agentic_Private_Brain and push vectors to Weaviate Cloud
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$env:PYTHONPATH='.'; conda run -n $(CONDA_ENV) uv run python Agentic_Private_Brain/deployment_scripts/ingest_private_brain.py"
else
	PYTHONPATH=. conda run -n $(CONDA_ENV) uv run python Agentic_Private_Brain/deployment_scripts/ingest_private_brain.py
endif

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
	docker run -p $(PORT):$(PORT) --env-file .auth/.env -v $(CURDIR)/.auth:/app/.auth -v $(CURDIR)/data:/app/data -v $(GCLOUD_CONFIG_DIR):/root/.config/gcloud:ro $(IMAGE_NAME)


docker-stop: ## Stop any running containers for this project
	@echo "Stopping $(IMAGE_NAME) containers..."
ifeq ($(OS),Windows_NT)
	@powershell -Command "docker ps -q --filter ancestor=$(IMAGE_NAME) | ForEach-Object { docker stop $$_ } 2>$$null; exit 0"
else
	docker stop $$(docker ps -q --filter ancestor=$(IMAGE_NAME)) 2>/dev/null || true
endif

deploy:
ifeq ($(OS),Windows_NT)
	@powershell -Command '\
		if (!(Test-Path .auth/.env)) { Write-Error "Error: .env file not found."; exit 1 } \
		Get-Content .auth/.env | ForEach-Object { \
			if ($$PSItem -match "^([^=]+)=(.*)$$") { \
				[System.Environment]::SetEnvironmentVariable($$Matches[1], $$Matches[2]) \
			} \
		}; \
		$$env:SERVICE_ACCOUNT_NAME = "$$env:FUNCTION_NAME-sa"; \
		$$env:SERVICE_ACCOUNT_EMAIL = "$$env:SERVICE_ACCOUNT_NAME@$$env:PROJECT_ID.iam.gserviceaccount.com"; \
		gcloud run deploy $$env:FUNCTION_NAME \
		  --base-image=python312 \
		  --project=$$env:PROJECT_ID \
		  --region=$$env:GOOGLE_CLOUD_REGION \
		  --source=./src/infrastructure/billing_killswitch/ \
		  --function=disable_billing_for_projects \
		  --no-allow-unauthenticated \
		  --execution-environment=gen1 \
		  --cpu=0.2 \
		  --memory=256Mi \
		  --concurrency=1 \
		  --min-instances=0 \
		  --max-instances=1 \
		  --service-account="$$env:SERVICE_ACCOUNT_EMAIL" \
		  --set-env-vars LOG_LEVEL=$$env:LOG_LEVEL,SIMULATE_DEACTIVATION=$$env:SIMULATE_DEACTIVATION \
	'
else
	@if [ ! -f .auth/.env ]; then echo "Error: .env file not found."; exit 1; fi
	@source .auth/.env && \
	export SERVICE_ACCOUNT_NAME="$$FUNCTION_NAME-sa" && \
	export SERVICE_ACCOUNT_EMAIL="$$SERVICE_ACCOUNT_NAME@$$PROJECT_ID.iam.gserviceaccount.com" && \
	gcloud run deploy $$FUNCTION_NAME \
	  --base-image=python312 \
	  --project=$$PROJECT_ID \
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
endif

# --- Maintenance & Cleanup ---
clean: ## Remove temporary files and archive backups to .legacy_hr
ifeq ($(OS),Windows_NT)
	@echo "Archiving .bk files to .legacy_hr..."
	@powershell -Command "if (!(Test-Path .legacy_hr)) { New-Item -ItemType Directory -Force .legacy_hr | Out-Null }"
	@powershell -Command 'Get-ChildItem -Path . -Filter "*.bk*" -Depth 2 | ForEach-Object { Move-Item -Path $$PSItem.FullName -Destination .legacy_hr\ -Force }'
	@echo "Cleaning Python cache files..."
	@powershell -Command "Get-ChildItem -Path . -Filter '*.pyc' -Recurse | Remove-Item -Force"
	@powershell -Command "Get-ChildItem -Path . -Filter '__pycache__' -Recurse | Remove-Item -Recurse -Force"
else
	@echo "Archiving .bk files to .legacy_hr..."
	@mkdir -p .legacy_hr
	@find . -maxdepth 2 -name "*.bk" -exec mv {} .legacy_hr/ \;
	@echo "Cleaning Python cache files..."
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -delete
endif
	@echo "Cleanup complete."
