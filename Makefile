# Goat Prediction Ultimate - Makefile
# Version: 3.0.0
# Author: Goat Prediction Team
# License: MIT

.DEFAULT_GOAL := help

# Configuration
PROJECT_NAME := goat-prediction-ultimate
VERSION := 3.0.0
PYTHON_VERSION := 3.11.7
NODE_VERSION := 18.18.2
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_FILES := -f docker-compose.yml -f docker-compose.override.yml

# Colors for output
COLOR_RESET := \033[0m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_BLUE := \033[34m
COLOR_MAGENTA := \033[35m
COLOR_CYAN := \033[36m
COLOR_WHITE := \033[37m
COLOR_BOLD := \033[1m

# Docker services
SERVICES := postgres redis timescaledb kafka zookeeper elasticsearch kibana \
            mlflow minio prometheus grafana alertmanager \
            api-gateway prediction-engine frontend admin-dashboard \
            nginx certbot backup fluentd

# Paths
BACKEND_DIR := backend
FRONTEND_DIR := frontend
ML_DIR := mlops
INFRA_DIR := infrastructure
SCRIPTS_DIR := scripts
TESTS_DIR := tests
DOCS_DIR := docs
DATA_DIR := data

# Python paths
PYTHONPATH := $(BACKEND_DIR)/prediction-engine/src:$(BACKEND_DIR)/api-gateway/src

# Environment detection
ifeq ($(ENV), production)
	DOCKER_COMPOSE_FILES := -f docker-compose.yml -f docker-compose.prod.yml
	ENV_SUFFIX := prod
else ifeq ($(ENV), test)
	DOCKER_COMPOSE_FILES := -f docker-compose.yml -f docker-compose.test.yml
	ENV_SUFFIX := test
else ifeq ($(ENV), dev)
	DOCKER_COMPOSE_FILES := -f docker-compose.dev.yml
	ENV_SUFFIX := dev
else
	ENV_SUFFIX := dev
endif

# Docker Compose command with environment
DC := $(DOCKER_COMPOSE) $(DOCKER_COMPOSE_FILES)

# Check if commands are available
HAS_DOCKER := $(shell command -v docker 2> /dev/null)
HAS_DOCKER_COMPOSE := $(shell command -v docker-compose 2> /dev/null)
HAS_PYTHON := $(shell command -v python3 2> /dev/null)
HAS_NODE := $(shell command -v node 2> /dev/null)
HAS_NPM := $(shell command -v npm 2> /dev/null)

.PHONY: help
help: ## Display this help message
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)Goat Prediction Ultimate - Makefile$(COLOR_RESET)"
	@echo "$(COLOR_BOLD)Version: $(VERSION)$(COLOR_RESET)"
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_YELLOW)Usage:$(COLOR_RESET)"
	@echo "  make [target]"
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_YELLOW)Environment:$(COLOR_RESET)"
	@echo "  ENV=dev|test|prod  Set environment (default: dev)"
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_YELLOW)Targets:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_GREEN)%-30s$(COLOR_RESET) %s\n", $$1, $$2}'

# ==============================================================================
# SETUP & INITIALIZATION
# ==============================================================================

.PHONY: init check-env setup install-deps

init: check-env setup install-deps ## Initialize project (check env, setup, install)

check-env: ## Check environment and dependencies
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔍 Checking environment...$(COLOR_RESET)"
	
	@echo "$(COLOR_WHITE)• Checking Docker...$(COLOR_RESET)"
	@if [ -z "$(HAS_DOCKER)" ]; then \
		echo "$(COLOR_YELLOW)  ⚠️  Docker not found. Please install Docker.$(COLOR_RESET)"; \
		exit 1; \
	else \
		echo "$(COLOR_GREEN)  ✅ Docker $(shell docker --version | cut -d' ' -f3 | cut -d',' -f1) found$(COLOR_RESET)"; \
	fi
	
	@echo "$(COLOR_WHITE)• Checking Docker Compose...$(COLOR_RESET)"
	@if [ -z "$(HAS_DOCKER_COMPOSE)" ]; then \
		echo "$(COLOR_YELLOW)  ⚠️  Docker Compose not found. Please install Docker Compose.$(COLOR_RESET)"; \
		exit 1; \
	else \
		echo "$(COLOR_GREEN)  ✅ Docker Compose $(shell docker-compose --version | cut -d' ' -f3 | cut -d',' -f1) found$(COLOR_RESET)"; \
	fi
	
	@echo "$(COLOR_WHITE)• Checking Python...$(COLOR_RESET)"
	@if [ -z "$(HAS_PYTHON)" ]; then \
		echo "$(COLOR_YELLOW)  ⚠️  Python3 not found. Please install Python 3.11+.$(COLOR_RESET)"; \
	else \
		echo "$(COLOR_GREEN)  ✅ Python $(shell python3 --version | cut -d' ' -f2) found$(COLOR_RESET)"; \
	fi
	
	@echo "$(COLOR_WHITE)• Checking Node.js...$(COLOR_RESET)"
	@if [ -z "$(HAS_NODE)" ]; then \
		echo "$(COLOR_YELLOW)  ⚠️  Node.js not found. Please install Node.js 18+.$(COLOR_RESET)"; \
	else \
		echo "$(COLOR_GREEN)  ✅ Node.js $(shell node --version) found$(COLOR_RESET)"; \
	fi
	
	@echo "$(COLOR_WHITE)• Checking npm...$(COLOR_RESET)"
	@if [ -z "$(HAS_NPM)" ]; then \
		echo "$(COLOR_YELLOW)  ⚠️  npm not found. Please install npm.$(COLOR_RESET)"; \
	else \
		echo "$(COLOR_GREEN)  ✅ npm $(shell npm --version) found$(COLOR_RESET)"; \
	fi
	
	@echo "$(COLOR_GREEN)✅ Environment check passed!$(COLOR_RESET)"

setup: ## Setup project configuration
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)⚙️  Setting up project...$(COLOR_RESET)"
	
	@if [ ! -f .env.local ]; then \
		echo "$(COLOR_WHITE)• Creating .env.local from template...$(COLOR_RESET)"; \
		cp .env.example .env.local; \
		echo "$(COLOR_YELLOW)  ⚠️  Please edit .env.local with your configuration$(COLOR_RESET)"; \
	else \
		echo "$(COLOR_GREEN)  ✅ .env.local already exists$(COLOR_RESET)"; \
	fi
	
	@echo "$(COLOR_WHITE)• Creating required directories...$(COLOR_RESET)"
	@mkdir -p data/development data/test data/production \
		models/development models/test models/production \
		logs/development logs/test logs/production \
		.backups .cache .tmp
	
	@echo "$(COLOR_WHITE)• Setting up git hooks...$(COLOR_RESET)"
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
		pre-commit install --hook-type commit-msg; \
		echo "$(COLOR_GREEN)  ✅ Git hooks installed$(COLOR_RESET)"; \
	else \
		echo "$(COLOR_YELLOW)  ⚠️  pre-commit not found, skipping git hooks$(COLOR_RESET)"; \
	fi
	
	@echo "$(COLOR_GREEN)✅ Project setup complete!$(COLOR_RESET)"

install-deps: ## Install project dependencies
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📦 Installing dependencies...$(COLOR_RESET)"
	
	@echo "$(COLOR_WHITE)• Installing Python dependencies...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && pip install -e .[dev] && cd ../..
	@cd $(BACKEND_DIR)/api-gateway && pip install -e .[dev] && cd ../..
	
	@echo "$(COLOR_WHITE)• Installing Node.js dependencies...$(COLOR_RESET)"
	@cd $(FRONTEND_DIR)/web-app && npm install && cd ../..
	@cd $(FRONTEND_DIR)/admin-dashboard && npm install && cd ../..
	
	@echo "$(COLOR_WHITE)• Installing ML dependencies...$(COLOR_RESET)"
	@cd $(ML_DIR) && pip install -r requirements.txt && cd ..
	
	@echo "$(COLOR_GREEN)✅ Dependencies installed!$(COLOR_RESET)"

# ==============================================================================
# DOCKER OPERATIONS
# ==============================================================================

.PHONY: up down restart logs ps clean-docker

up: ## Start all Docker services
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🚀 Starting services in $(ENV_SUFFIX) environment...$(COLOR_RESET)"
	@$(DC) up -d --remove-orphans
	@echo "$(COLOR_GREEN)✅ Services started!$(COLOR_RESET)"
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)📊 Service Status:$(COLOR_RESET)"
	@$(DC) ps
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)🌐 Available URLs:$(COLOR_RESET)"
	@echo "  Frontend:        http://localhost:3000"
	@echo "  API Gateway:     http://localhost:8000"
	@echo "  Prediction API:  http://localhost:8001"
	@echo "  Adminer (DB):    http://localhost:8080"
	@echo "  PGAdmin:         http://localhost:5050"
	@echo "  Grafana:         http://localhost:3001"
	@echo "  MLflow:          http://localhost:5000"
	@echo "  Kibana:          http://localhost:5601"
	@echo "  Prometheus:      http://localhost:9090"

down: ## Stop all Docker services
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🛑 Stopping services...$(COLOR_RESET)"
	@$(DC) down
	@echo "$(COLOR_GREEN)✅ Services stopped!$(COLOR_RESET)"

restart: down up ## Restart all Docker services

logs: ## Show logs from all services
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📝 Showing logs...$(COLOR_RESET)"
	@$(DC) logs -f --tail=100

logs-%: ## Show logs for specific service
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📝 Showing logs for $*...$(COLOR_RESET)"
	@$(DC) logs -f --tail=100 $*

ps: ## Show status of all services
	@$(DC) ps

clean-docker: ## Clean Docker containers, volumes, and images
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🧹 Cleaning Docker...$(COLOR_RESET)"
	@$(DC) down -v --remove-orphans
	@docker system prune -af
	@echo "$(COLOR_GREEN)✅ Docker cleaned!$(COLOR_RESET)"

# ==============================================================================
# DATABASE OPERATIONS
# ==============================================================================

.PHONY: db-init db-migrate db-seed db-backup db-restore db-shell

db-init: ## Initialize databases
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🗄️  Initializing databases...$(COLOR_RESET)"
	@$(DC) exec postgres psql -U goat_dev -d goat_prediction_dev -f /docker-entrypoint-initdb.d/001_initial_schema.sql
	@$(DC) exec timescaledb psql -U timescale_dev -d goat_prediction_timeseries_dev -f /docker-entrypoint-initdb.d/001_hypertables.sql
	@echo "$(COLOR_GREEN)✅ Databases initialized!$(COLOR_RESET)"

db-migrate: ## Run database migrations
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔄 Running migrations...$(COLOR_RESET)"
	@$(DC) exec api-gateway alembic upgrade head
	@echo "$(COLOR_GREEN)✅ Migrations complete!$(COLOR_RESET)"

db-seed: ## Seed databases with sample data
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🌱 Seeding databases...$(COLOR_RESET)"
	@$(DC) run --rm db-seed-dev
	@echo "$(COLOR_GREEN)✅ Databases seeded!$(COLOR_RESET)"

db-backup: ## Backup databases
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)💾 Backing up databases...$(COLOR_RESET)"
	@mkdir -p .backups/$(shell date +%Y%m%d)
	@$(DC) exec postgres pg_dump -U goat_dev goat_prediction_dev > .backups/$(shell date +%Y%m%d)/postgres_backup.sql
	@$(DC) exec timescaledb pg_dump -U timescale_dev goat_prediction_timeseries_dev > .backups/$(shell date +%Y%m%d)/timescaledb_backup.sql
	@echo "$(COLOR_GREEN)✅ Backups saved to .backups/$(shell date +%Y%m%d)/$(COLOR_RESET)"

db-restore: ## Restore databases from backup
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)↩️  Restoring databases...$(COLOR_RESET)"
	@if [ -z "$(BACKUP_DATE)" ]; then \
		echo "$(COLOR_YELLOW)Usage: make db-restore BACKUP_DATE=YYYYMMDD$(COLOR_RESET)"; \
		exit 1; \
	fi
	@$(DC) exec -T postgres psql -U goat_dev -d goat_prediction_dev < .backups/$(BACKUP_DATE)/postgres_backup.sql
	@$(DC) exec -T timescaledb psql -U timescale_dev -d goat_prediction_timeseries_dev < .backups/$(BACKUP_DATE)/timescaledb_backup.sql
	@echo "$(COLOR_GREEN)✅ Databases restored from $(BACKUP_DATE)!$(COLOR_RESET)"

db-shell: ## Open database shell
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🐚 Opening database shell...$(COLOR_RESET)"
	@$(DC) exec postgres psql -U goat_dev -d goat_prediction_dev

# ==============================================================================
# DEVELOPMENT
# ==============================================================================

.PHONY: dev-backend dev-frontend dev-ml dev-all

dev-backend: ## Start backend development servers
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🚀 Starting backend development...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/api-gateway && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
	@cd $(BACKEND_DIR)/prediction-engine && uvicorn src.main:app --reload --host 0.0.0.0 --port 8001 &
	@echo "$(COLOR_GREEN)✅ Backend servers started!$(COLOR_RESET)"
	@echo "  API Gateway:     http://localhost:8000"
	@echo "  Prediction API:  http://localhost:8001"

dev-frontend: ## Start frontend development servers
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🚀 Starting frontend development...$(COLOR_RESET)"
	@cd $(FRONTEND_DIR)/web-app && npm run dev &
	@cd $(FRONTEND_DIR)/admin-dashboard && npm run dev &
	@echo "$(COLOR_GREEN)✅ Frontend servers started!$(COLOR_RESET)"
	@echo "  Web App:         http://localhost:3000"
	@echo "  Admin Dashboard: http://localhost:3002"

dev-ml: ## Start ML development environment
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🧠 Starting ML development...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root &
	@echo "$(COLOR_GREEN)✅ ML environment started!$(COLOR_RESET)"
	@echo "  Jupyter Lab:     http://localhost:8888"

dev-all: dev-backend dev-frontend dev-ml ## Start all development servers

# ==============================================================================
# TESTING
# ==============================================================================

.PHONY: test test-unit test-integration test-e2e test-coverage test-performance

test: test-unit test-integration test-e2e ## Run all tests

test-unit: ## Run unit tests
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🧪 Running unit tests...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && pytest tests/unit/ -v --tb=short
	@cd $(BACKEND_DIR)/api-gateway && pytest tests/unit/ -v --tb=short
	@cd $(FRONTEND_DIR)/web-app && npm test -- --watchAll=false
	@echo "$(COLOR_GREEN)✅ Unit tests passed!$(COLOR_RESET)"

test-integration: ## Run integration tests
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔗 Running integration tests...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && pytest tests/integration/ -v --tb=short
	@cd $(BACKEND_DIR)/api-gateway && pytest tests/integration/ -v --tb=short
	@echo "$(COLOR_GREEN)✅ Integration tests passed!$(COLOR_RESET)"

test-e2e: ## Run end-to-end tests
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🏁 Running E2E tests...$(COLOR_RESET)"
	@cd $(TESTS_DIR)/e2e && npm test
	@echo "$(COLOR_GREEN)✅ E2E tests passed!$(COLOR_RESET)"

test-coverage: ## Run tests with coverage report
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📊 Running tests with coverage...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && \
		pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@cd $(BACKEND_DIR)/api-gateway && \
		pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "$(COLOR_GREEN)✅ Coverage reports generated!$(COLOR_RESET)"
	@echo "  Open: backend/prediction-engine/htmlcov/index.html"
	@echo "  Open: backend/api-gateway/htmlcov/index.html"

test-performance: ## Run performance tests
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)⚡ Running performance tests...$(COLOR_RESET)"
	@cd $(TESTS_DIR)/performance && k6 run api-load-test.js
	@echo "$(COLOR_GREEN)✅ Performance tests complete!$(COLOR_RESET)"

# ==============================================================================
# CODE QUALITY
# ==============================================================================

.PHONY: lint lint-fix format format-check security check

lint: ## Run all linters
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔍 Running linters...$(COLOR_RESET)"
	@echo "$(COLOR_WHITE)• Linting Python...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && flake8 src tests
	@cd $(BACKEND_DIR)/api-gateway && flake8 src tests
	@echo "$(COLOR_WHITE)• Linting TypeScript...$(COLOR_RESET)"
	@cd $(FRONTEND_DIR)/web-app && npm run lint
	@cd $(FRONTEND_DIR)/admin-dashboard && npm run lint
	@echo "$(COLOR_WHITE)• Linting CSS...$(COLOR_RESET)"
	@cd $(FRONTEND_DIR)/web-app && npm run stylelint
	@echo "$(COLOR_GREEN)✅ Linting passed!$(COLOR_RESET)"

lint-fix: ## Run linters and auto-fix issues
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔧 Fixing lint issues...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && black src tests && isort src tests
	@cd $(BACKEND_DIR)/api-gateway && black src tests && isort src tests
	@cd $(FRONTEND_DIR)/web-app && npm run lint:fix
	@cd $(FRONTEND_DIR)/admin-dashboard && npm run lint:fix
	@echo "$(COLOR_GREEN)✅ Lint fixes applied!$(COLOR_RESET)"

format: ## Format all code
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🎨 Formatting code...$(COLOR_RESET)"
	@pre-commit run --all-files
	@echo "$(COLOR_GREEN)✅ Code formatted!$(COLOR_RESET)"

format-check: ## Check code formatting
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔍 Checking code format...$(COLOR_RESET)"
	@pre-commit run --all-files --hook-stage manual
	@echo "$(COLOR_GREEN)✅ Code format check passed!$(COLOR_RESET)"

security: ## Run security checks
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔒 Running security checks...$(COLOR_RESET)"
	@echo "$(COLOR_WHITE)• Scanning Python dependencies...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && safety check
	@cd $(BACKEND_DIR)/api-gateway && safety check
	@echo "$(COLOR_WHITE)• Scanning Node.js dependencies...$(COLOR_RESET)"
	@cd $(FRONTEND_DIR)/web-app && npm audit
	@cd $(FRONTEND_DIR)/admin-dashboard && npm audit
	@echo "$(COLOR_WHITE)• Scanning Docker images...$(COLOR_RESET)"
	@docker scan goat-prediction/api-gateway
	@docker scan goat-prediction/prediction-engine
	@echo "$(COLOR_GREEN)✅ Security checks complete!$(COLOR_RESET)"

check: lint format-check security ## Run all checks (lint, format, security)

# ==============================================================================
# ML OPERATIONS
# ==============================================================================

.PHONY: ml-train ml-evaluate ml-serve ml-monitor

ml-train: ## Train ML models
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🤖 Training ML models...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && \
		python scripts/train_models.py --sport football --market match_winner
	@echo "$(COLOR_GREEN)✅ Model training complete!$(COLOR_RESET)"

ml-evaluate: ## Evaluate ML models
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📈 Evaluating ML models...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && \
		python scripts/evaluate_models.py --sport all --output reports/
	@echo "$(COLOR_GREEN)✅ Model evaluation complete!$(COLOR_RESET)"

ml-serve: ## Serve ML models
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🚀 Serving ML models...$(COLOR_RESET)"
	@cd $(ML_DIR)/serving && docker-compose up -d
	@echo "$(COLOR_GREEN)✅ Models serving started!$(COLOR_RESET)"
	@echo "  Triton Server:   http://localhost:8000"
	@echo "  MLflow Models:   http://localhost:5001"

ml-monitor: ## Monitor ML models
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)👁️  Monitoring ML models...$(COLOR_RESET)"
	@cd $(ML_DIR) && mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000 &
	@echo "$(COLOR_GREEN)✅ ML monitoring started!$(COLOR_RESET)"
	@echo "  MLflow UI:       http://localhost:5000"

# ==============================================================================
# DEPLOYMENT
# ==============================================================================

.PHONY: build push deploy deploy-staging deploy-production

build: ## Build all Docker images
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🏗️  Building Docker images...$(COLOR_RESET)"
	@$(DC) build --parallel
	@echo "$(COLOR_GREEN)✅ Docker images built!$(COLOR_RESET)"

push: ## Push Docker images to registry
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)⬆️  Pushing Docker images...$(COLOR_RESET)"
	@$(foreach service,$(SERVICES), \
		docker tag goat-prediction-$(service) registry.goat-prediction.com/$(service):latest; \
		docker push registry.goat-prediction.com/$(service):latest; \
	)
	@echo "$(COLOR_GREEN)✅ Docker images pushed!$(COLOR_RESET)"

deploy: ## Deploy to Kubernetes
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🚀 Deploying to Kubernetes...$(COLOR_RESET)"
	@cd $(INFRA_DIR)/kubernetes && kubectl apply -k .
	@echo "$(COLOR_GREEN)✅ Deployment complete!$(COLOR_RESET)"

deploy-staging: ## Deploy to staging environment
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🚀 Deploying to staging...$(COLOR_RESET)"
	@ENV=staging $(DC) -f docker-compose.staging.yml up -d
	@echo "$(COLOR_GREEN)✅ Staging deployment complete!$(COLOR_RESET)"

deploy-production: ## Deploy to production environment
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🚀 Deploying to production...$(COLOR_RESET)"
	@ENV=production $(DC) -f docker-compose.prod.yml up -d
	@echo "$(COLOR_GREEN)✅ Production deployment complete!$(COLOR_RESET)"

# ==============================================================================
# MONITORING & LOGS
# ==============================================================================

.PHONY: monitor logs-tail metrics alerts

monitor: ## Open monitoring dashboards
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📊 Opening monitoring dashboards...$(COLOR_RESET)"
	@open http://localhost:3001  # Grafana
	@open http://localhost:5601  # Kibana
	@open http://localhost:9090  # Prometheus
	@echo "$(COLOR_GREEN)✅ Monitoring dashboards opened!$(COLOR_RESET)"

logs-tail: ## Tail all logs in real-time
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📝 Tailing all logs...$(COLOR_RESET)"
	@$(DC) logs -f --tail=50

metrics: ## Show current metrics
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📈 Current metrics...$(COLOR_RESET)"
	@curl -s http://localhost:9090/api/v1/query?query=up | jq .
	@echo "$(COLOR_GREEN)✅ Metrics retrieved!$(COLOR_RESET)"

alerts: ## Show active alerts
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🚨 Active alerts...$(COLOR_RESET)"
	@curl -s http://localhost:9093/api/v2/alerts | jq .
	@echo "$(COLOR_GREEN)✅ Alerts retrieved!$(COLOR_RESET)"

# ==============================================================================
# DATA OPERATIONS
# ==============================================================================

.PHONY: data-collect data-process data-export data-clean

data-collect: ## Collect sports data
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📥 Collecting sports data...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && \
		python scripts/collect_data.py --sport football --days 7
	@echo "$(COLOR_GREEN)✅ Data collection complete!$(COLOR_RESET)"

data-process: ## Process collected data
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔄 Processing data...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && \
		python scripts/process_data.py --input data/raw --output data/processed
	@echo "$(COLOR_GREEN)✅ Data processing complete!$(COLOR_RESET)"

data-export: ## Export data for analysis
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📤 Exporting data...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && \
		python scripts/export_data.py --format csv --output exports/
	@echo "$(COLOR_GREEN)✅ Data export complete!$(COLOR_RESET)"

data-clean: ## Clean data directories
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🧹 Cleaning data...$(COLOR_RESET)"
	@rm -rf data/raw/* data/processed/* data/cache/*
	@echo "$(COLOR_GREEN)✅ Data cleaned!$(COLOR_RESET)"

# ==============================================================================
# UTILITIES
# ==============================================================================

.PHONY: clean update version status health

clean: ## Clean project (remove generated files)
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🧹 Cleaning project...$(COLOR_RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.pyd" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type f -name "coverage.xml" -delete
	@echo "$(COLOR_GREEN)✅ Project cleaned!$(COLOR_RESET)"

update: ## Update project dependencies
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔄 Updating dependencies...$(COLOR_RESET)"
	@cd $(BACKEND_DIR)/prediction-engine && pip install --upgrade -e .[dev]
	@cd $(BACKEND_DIR)/api-gateway && pip install --upgrade -e .[dev]
	@cd $(FRONTEND_DIR)/web-app && npm update
	@cd $(FRONTEND_DIR)/admin-dashboard && npm update
	@echo "$(COLOR_GREEN)✅ Dependencies updated!$(COLOR_RESET)"

version: ## Show project version
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)$(PROJECT_NAME) v$(VERSION)$(COLOR_RESET)"
	@echo "Python: $(PYTHON_VERSION)"
	@echo "Node.js: $(NODE_VERSION)"
	@echo "Environment: $(ENV_SUFFIX)"

status: ## Show project status
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)📊 Project Status$(COLOR_RESET)"
	@echo ""
	@echo "$(COLOR_BOLD)Docker Services:$(COLOR_RESET)"
	@$(DC) ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "$(COLOR_BOLD)Disk Usage:$(COLOR_RESET)"
	@du -sh . | awk '{print "Total: " $1}'
	@du -sh data/ models/ logs/ .cache/ | awk '{print $2 ": " $1}'
	@echo ""
	@echo "$(COLOR_BOLD)Git Status:$(COLOR_RESET)"
	@git status --short --branch

health: ## Check system health
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)❤️  Checking system health...$(COLOR_RESET)"
	@echo "$(COLOR_WHITE)• Docker health...$(COLOR_RESET)"
	@docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(healthy|unhealthy)"
	@echo ""
	@echo "$(COLOR_WHITE)• API health...$(COLOR_RESET)"
	@curl -s http://localhost:8000/health | jq .status || echo "API Gateway: ❌"
	@curl -s http://localhost:8001/health | jq .status || echo "Prediction Engine: ❌"
	@echo ""
	@echo "$(COLOR_WHITE)• Database health...$(COLOR_RESET)"
	@$(DC) exec postgres pg_isready -U goat_dev && echo "PostgreSQL: ✅" || echo "PostgreSQL: ❌"
	@$(DC) exec timescaledb pg_isready -U timescale_dev && echo "TimescaleDB: ✅" || echo "TimescaleDB: ❌"
	@echo ""
	@echo "$(COLOR_GREEN)✅ Health check complete!$(COLOR_RESET)"

# ==============================================================================
# BACKUP & RECOVERY
# ==============================================================================

.PHONY: backup-full backup-db backup-models restore

backup-full: ## Create full backup
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)💾 Creating full backup...$(COLOR_RESET)"
	@mkdir -p .backups/full_$(shell date +%Y%m%d_%H%M%S)
	@make db-backup BACKUP_DATE=full_$(shell date +%Y%m%d_%H%M%S)
	@cp -r models/ .backups/full_$(shell date +%Y%m%d_%H%M%S)/
	@cp -r data/ .backups/full_$(shell date +%Y%m%d_%H%M%S)/
	@tar -czf .backups/full_$(shell date +%Y%m%d_%H%M%S).tar.gz .backups/full_$(shell date +%Y%m%d_%H%M%S)
	@echo "$(COLOR_GREEN)✅ Full backup created: .backups/full_$(shell date +%Y%m%d_%H%M%S).tar.gz$(COLOR_RESET)"

backup-db: db-backup ## Alias for db-backup

backup-models: ## Backup ML models
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)💾 Backing up ML models...$(COLOR_RESET)"
	@mkdir -p .backups/models_$(shell date +%Y%m%d)
	@cp -r models/ .backups/models_$(shell date +%Y%m%d)/
	@echo "$(COLOR_GREEN)✅ Models backed up to .backups/models_$(shell date +%Y%m%d)/$(COLOR_RESET)"

restore: ## Restore from backup (specify BACKUP_FILE)
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)↩️  Restoring from backup...$(COLOR_RESET)"
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "$(COLOR_YELLOW)Usage: make restore BACKUP_FILE=path/to/backup.tar.gz$(COLOR_RESET)"; \
		exit 1; \
	fi
	@tar -xzf $(BACKUP_FILE) -C .backups/
	@echo "$(COLOR_GREEN)✅ Backup extracted. Run specific restore commands.$(COLOR_RESET)"

# ==============================================================================
# DOCUMENTATION
# ==============================================================================

.PHONY: docs docs-serve docs-build docs-deploy

docs: ## Generate documentation
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📚 Generating documentation...$(COLOR_RESET)"
	@cd $(DOCS_DIR) && make html
	@echo "$(COLOR_GREEN)✅ Documentation generated!$(COLOR_RESET)"

docs-serve: ## Serve documentation locally
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🌐 Serving documentation...$(COLOR_RESET)"
	@cd $(DOCS_DIR)/_build/html && python -m http.server 8002 &
	@echo "$(COLOR_GREEN)✅ Documentation server started!$(COLOR_RESET)"
	@echo "  Open: http://localhost:8002"

docs-build: ## Build documentation for production
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🏗️  Building documentation...$(COLOR_RESET)"
	@cd $(DOCS_DIR) && make clean && make html
	@echo "$(COLOR_GREEN)✅ Documentation built!$(COLOR_RESET)"

docs-deploy: ## Deploy documentation
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🚀 Deploying documentation...$(COLOR_RESET)"
	@cd $(DOCS_DIR) && make deploy
	@echo "$(COLOR_GREEN)✅ Documentation deployed!$(COLOR_RESET)"

# ==============================================================================
# DEVELOPMENT TOOLS
# ==============================================================================

.PHONY: shell shell-backend shell-frontend shell-db

shell: ## Open shell in running container
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🐚 Opening shell...$(COLOR_RESET)"
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(COLOR_YELLOW)Usage: make shell SERVICE=service_name$(COLOR_RESET)"; \
		echo "$(COLOR_WHITE)Available services:$(COLOR_RESET)"; \
		$(DC) ps --services | tr ' ' '\n' | sort; \
		exit 1; \
	fi
	@$(DC) exec $(SERVICE) sh

shell-backend: ## Open shell in backend service
	@make shell SERVICE=prediction-engine

shell-frontend: ## Open shell in frontend service
	@make shell SERVICE=frontend

shell-db: ## Open shell in database
	@make shell SERVICE=postgres

# ==============================================================================
# MIGRATION HELPERS
# ==============================================================================

.PHONY: migrate-create migrate-rollback migrate-history

migrate-create: ## Create new migration
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📝 Creating migration...$(COLOR_RESET)"
	@if [ -z "$(MESSAGE)" ]; then \
		echo "$(COLOR_YELLOW)Usage: make migrate-create MESSAGE=\"description\"$(COLOR_RESET)"; \
		exit 1; \
	fi
	@$(DC) exec api-gateway alembic revision --autogenerate -m "$(MESSAGE)"
	@echo "$(COLOR_GREEN)✅ Migration created!$(COLOR_RESET)"

migrate-rollback: ## Rollback last migration
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)↩️  Rolling back migration...$(COLOR_RESET)"
	@$(DC) exec api-gateway alembic downgrade -1
	@echo "$(COLOR_GREEN)✅ Migration rolled back!$(COLOR_RESET)"

migrate-history: ## Show migration history
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)📜 Migration history...$(COLOR_RESET)"
	@$(DC) exec api-gateway alembic history --verbose

# ==============================================================================
# SPECIAL TARGETS
# ==============================================================================

.PHONY: demo reset prod-simulate

demo: ## Run demo mode with sample data
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🎬 Starting demo mode...$(COLOR_RESET)"
	@make db-seed
	@make ml-train
	@echo "$(COLOR_GREEN)✅ Demo ready!$(COLOR_RESET)"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Try making predictions for upcoming matches"

reset: clean-docker clean ## Reset project to clean state
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🔄 Resetting project...$(COLOR_RESET)"
	@rm -rf data/ models/ logs/ .backups/ .cache/ .tmp/
	@mkdir -p data/development models/development logs/development
	@echo "$(COLOR_GREEN)✅ Project reset!$(COLOR_RESET)"

prod-simulate: ## Simulate production environment locally
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)🏭 Simulating production...$(COLOR_RESET)"
	@ENV=production $(DC) -f docker-compose.prod.yml up -d --scale api-gateway=3 --scale prediction-engine=3
	@echo "$(COLOR_GREEN)✅ Production simulation started!$(COLOR_RESET)"
	@echo "  Load Balancer: http://localhost"
	@echo "  API Gateway:   http://localhost/api"
	@echo "  Monitoring:    http://localhost/monitoring"

# ==============================================================================
# INTERNAL TARGETS
# ==============================================================================

.PHONY: _check-service _wait-for-service _run-tests

_check-service:
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(COLOR_RED)Error: SERVICE variable not set$(COLOR_RESET)"; \
		exit 1; \
	fi

_wait-for-service: _check-service
	@echo "$(COLOR_WHITE)⏳ Waiting for $(SERVICE) to be healthy...$(COLOR_RESET)"
	@timeout 120 bash -c "until docker-compose ps $(SERVICE) | grep -q '(healthy)'; do sleep 2; done" || \
		(echo "$(COLOR_RED)❌ Service $(SERVICE) failed to become healthy$(COLOR_RESET)" && exit 1)
	@echo "$(COLOR_GREEN)✅ Service $(SERVICE) is healthy$(COLOR_RESET)"

_run-tests:
	@echo "$(COLOR_WHITE)🧪 Running $(TEST_TYPE) tests...$(COLOR_RESET)"
	@cd $(TEST_DIR) && $(TEST_CMD)

# ==============================================================================
# PHONY TARGET DECLARATION
# ==============================================================================

.PHONY: $(SERVICES)

# Auto-generated service targets
define SERVICE_TARGET
.PHONY: $(1)
$(1): ## Start/stop specific service
	@if [ "$$(MAKECMDGOALS)" = "$(1)" ]; then \
		echo "$(COLOR_BOLD)$(COLOR_BLUE)🚀 Starting $(1)...$(COLOR_RESET)"; \
		$(DC) up -d $(1); \
		echo "$(COLOR_GREEN)✅ $(1) started!$(COLOR_RESET)"; \
	elif [ "$$(MAKECMDGOALS)" = "stop-$(1)" ]; then \
		echo "$(COLOR_BOLD)$(COLOR_BLUE)🛑 Stopping $(1)...$(COLOR_RESET)"; \
		$(DC) stop $(1); \
		echo "$(COLOR_GREEN)✅ $(1) stopped!$(COLOR_RESET)"; \
	elif [ "$$(MAKECMDGOALS)" = "restart-$(1)" ]; then \
		echo "$(COLOR_BOLD)$(COLOR_BLUE)🔄 Restarting $(1)...$(COLOR_RESET)"; \
		$(DC) restart $(1); \
		echo "$(COLOR_GREEN)✅ $(1) restarted!$(COLOR_RESET)"; \
	fi
endef

# Generate service targets
$(foreach service,$(SERVICES),$(eval $(call SERVICE_TARGET,$(service))))

# ==============================================================================
# FINAL MESSAGE
# ==============================================================================

.DONE:
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_GREEN)✅ Operation completed successfully!$(COLOR_RESET)"
	@echo "$(COLOR_WHITE)Goat Prediction Ultimate - Making sports predictions smarter.$(COLOR_RESET)"
