.PHONY: help setup build start stop clean test deploy logs

# Colors
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[0;33m
BLUE=\033[0;34m
NC=\033[0m # No Color

# Help
help:
	@echo "🚀 ${GREEN}GOAT PREDICTION ULTIMATE - Commands${NC}"
	@echo ""
	@echo "${YELLOW}Setup:${NC}"
	@echo "  make setup           Setup development environment"
	@echo "  make init            Initialize project"
	@echo ""
	@echo "${YELLOW}Development:${NC}"
	@echo "  make dev             Start development environment"
	@echo "  make build           Build all services"
	@echo "  make start           Start production services"
	@echo "  make stop            Stop all services"
	@echo "  make clean           Clean docker resources"
	@echo ""
	@echo "${YELLOW}Database:${NC}"
	@echo "  make db-init         Initialize database"
	@echo "  make db-migrate      Run database migrations"
	@echo "  make db-reset        Reset database"
	@echo ""
	@echo "${YELLOW}Testing:${NC}"
	@echo "  make test            Run all tests"
	@echo "  make test-backend    Run backend tests"
	@echo "  make test-frontend   Run frontend tests"
	@echo ""
	@echo "${YELLOW}Monitoring:${NC}"
	@echo "  make monitor         Start monitoring stack"
	@echo "  make logs            View logs"
	@echo ""
	@echo "${YELLOW}Deployment:${NC}"
	@echo "  make deploy-dev      Deploy to development"
	@echo "  make deploy-prod     Deploy to production"

# Setup
setup:
	@echo "${BLUE}📦 Setting up development environment...${NC}"
	@cp .env.example .env.local
	@echo "${GREEN}✅ Created .env.local file${NC}"
	@echo "${YELLOW}⚠️  Please update .env.local with your configuration${NC}"

init:
	@echo "${BLUE}🚀 Initializing GOAT PREDICTION...${NC}"
	@mkdir -p .cache .logs .tmp .secrets
	@mkdir -p backend/{api-gateway,prediction-engine}/src
	@mkdir -p frontend/web-app/src
	@mkdir -p database/{migrations,seeds}
	@echo "${GREEN}✅ Project structure created${NC}"

# Development
dev:
	@echo "${BLUE}🚀 Starting development environment...${NC}"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

build:
	@echo "${BLUE}🔨 Building services...${NC}"
	@docker-compose build

start:
	@echo "${BLUE}🚀 Starting services...${NC}"
	@docker-compose up -d

stop:
	@echo "${BLUE}🛑 Stopping services...${NC}"
	@docker-compose down

clean:
	@echo "${BLUE}🧹 Cleaning up...${NC}"
	@docker-compose down -v --remove-orphans
	@docker system prune -f

# Database
db-init:
	@echo "${BLUE}🗄️  Initializing database...${NC}"
	@docker-compose exec postgres psql -U goat -d goat_prediction -f /docker-entrypoint-initdb.d/001_initial_schema.sql

db-migrate:
	@echo "${BLUE}🔄 Running migrations...${NC}"
	@cd backend/api-gateway && alembic upgrade head

db-reset:
	@echo "${RED}⚠️  Resetting database...${NC}"
	@read -p "Are you sure? This will delete all data! (y/N): " confirm && \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		docker volume rm goat-prediction_postgres_data; \
		echo "${GREEN}✅ Database reset${NC}"; \
	else \
		echo "${YELLOW}❌ Cancelled${NC}"; \
	fi

# Testing
test:
	@echo "${BLUE}🧪 Running all tests...${NC}"
	@cd backend/api-gateway && python -m pytest tests/ -v
	@cd frontend/web-app && npm test

test-backend:
	@echo "${BLUE}🧪 Running backend tests...${NC}"
	@cd backend/api-gateway && python -m pytest tests/ -v

test-frontend:
	@echo "${BLUE}🧪 Running frontend tests...${NC}"
	@cd frontend/web-app && npm test

# Monitoring
monitor:
	@echo "${BLUE}📊 Starting monitoring stack...${NC}"
	@docker-compose -f docker-compose.monitoring.yml up -d

logs:
	@echo "${BLUE}📝 Viewing logs...${NC}"
	@docker-compose logs -f

# Deployment
deploy-dev:
	@echo "${BLUE}🚀 Deploying to development...${NC}"
	@git push origin development
	@echo "${GREEN}✅ Triggered development deployment${NC}"

deploy-prod:
	@echo "${RED}⚠️  Deploying to production...${NC}"
	@read -p "Are you sure? (y/N): " confirm && \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git push origin main; \
		echo "${GREEN}✅ Triggered production deployment${NC}"; \
	else \
		echo "${YELLOW}❌ Cancelled${NC}"; \
	fi

# ML
train-models:
	@echo "${BLUE}🧠 Training ML models...${NC}"
	@cd backend/prediction-engine && python scripts/train_models.py

update-data:
	@echo "${BLUE}📊 Updating data...${NC}"
	@cd backend/prediction-engine && python scripts/update_data.py

# Backup
backup:
	@echo "${BLUE}💾 Creating backup...${NC}"
	@mkdir -p .backups/$(shell date +%Y%m%d_%H%M%S)
	@docker-compose exec postgres pg_dump -U goat goat_prediction > .backups/$(shell date +%Y%m%d_%H%M%S)/database.sql
	@echo "${GREEN}✅ Backup created${NC}"
