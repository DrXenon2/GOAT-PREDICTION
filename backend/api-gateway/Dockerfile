# ===========================================
# GOAT Prediction API Gateway - Dockerfile
# Production-ready multi-stage build
# Optimized for security, performance, and minimal size
# ===========================================

# ===========================================
# STAGE 1: Builder - Install dependencies
# ===========================================
FROM python:3.11-slim-bullseye AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Add poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    git \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    pkg-config \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && poetry --version

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install runtime dependencies only (no dev dependencies)
RUN poetry install --only main --no-root --no-ansi

# ===========================================
# STAGE 2: Development - For local development
# ===========================================
FROM python:3.11-slim-bullseye AS development

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app \
    ENVIRONMENT=development

# Install system dependencies for development
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    git \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    pkg-config \
    wget \
    ca-certificates \
    netcat-openbsd \
    postgresql-client \
    redis-tools \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy poetry installation from builder
COPY --from=builder /opt/poetry /opt/poetry
ENV PATH="/opt/poetry/bin:$PATH"

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install all dependencies (including dev)
RUN poetry install --no-root --no-ansi

# Create non-root user
RUN groupadd -r goat && useradd -r -g goat -m -d /home/goat -s /bin/bash goat \
    && chown -R goat:goat /app /home/goat

# Switch to non-root user
USER goat

# Copy application code
COPY --chown=goat:goat . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/tmp \
    && chmod -R 755 /app/logs /app/data /app/tmp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command for development
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===========================================
# STAGE 3: Production - Minimal runtime image
# ===========================================
FROM python:3.11-slim-bullseye AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app \
    ENVIRONMENT=production \
    UWSGI_PROCESSES=4 \
    UWSGI_THREADS=2 \
    UWSGI_HARAKIRI=30 \
    UWSGI_MAX_REQUESTS=1000 \
    UWSGI_BUFFER_SIZE=32768

# Install system dependencies for runtime only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libssl-dev \
    curl \
    ca-certificates \
    tzdata \
    # For health checks
    iputils-ping \
    dnsutils \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set timezone to UTC
RUN ln -sf /usr/share/zoneinfo/UTC /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata

# Create non-root user
RUN groupadd -r goat && useradd -r -g goat -m -d /home/goat -s /bin/bash goat \
    && mkdir -p /app \
    && chown -R goat:goat /app /home/goat

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=goat:goat . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/tmp /app/cache \
    && chmod -R 755 /app/logs /app/data /app/tmp /app/cache \
    && chown -R goat:goat /app

# Switch to non-root user
USER goat

# Create virtual environment and activate it
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install gunicorn for production (if not already installed)
RUN pip install --no-cache-dir gunicorn==21.2.0 uvicorn[standard]==0.24.0

# Copy only necessary files for production
COPY --chown=goat:goat src/ ./src/
COPY --chown=goat:goat pyproject.toml .
COPY --chown=goat:goat alembic.ini .
COPY --chown=goat:goat docker-entrypoint.sh .

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Health check (more strict in production)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Default command for production
CMD ["gunicorn", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--workers", "4", \
    "--threads", "2", \
    "--bind", "0.0.0.0:8000", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--log-level", "info", \
    "--timeout", "120", \
    "--keep-alive", "5", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "50", \
    "--graceful-timeout", "30", \
    "--worker-tmp-dir", "/dev/shm", \
    "src.main:app"]

# ===========================================
# STAGE 4: Testing - For CI/CD pipeline
# ===========================================
FROM development AS testing

# Set environment variables for testing
ENV ENVIRONMENT=testing \
    PYTEST_ADDOPTS="-v --tb=short"

# Install testing dependencies
RUN poetry install --with dev --no-root --no-ansi

# Copy test files
COPY --chown=goat:goat tests/ ./tests/

# Run tests
CMD ["pytest", "tests/", "--cov=src", "--cov-report=term-missing", "--cov-report=html"]

# ===========================================
# STAGE 5: Security Scan - For vulnerability scanning
# ===========================================
FROM production AS security-scan

USER root

# Install security scanning tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Trivy for container scanning
RUN wget https://github.com/aquasecurity/trivy/releases/download/v0.48.0/trivy_0.48.0_Linux-64bit.deb \
    && dpkg -i trivy_0.48.0_Linux-64bit.deb \
    && rm trivy_0.48.0_Linux-64bit.deb

# Install Grype for vulnerability scanning
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# Copy scanning scripts
COPY --chown=goat:goat scripts/security-scan.sh /app/scripts/security-scan.sh
RUN chmod +x /app/scripts/security-scan.sh

# Switch back to non-root user
USER goat

# Run security scan
CMD ["/app/scripts/security-scan.sh"]

# ===========================================
# STAGE 6: Performance - For benchmarking
# ===========================================
FROM production AS performance

USER root

# Install performance testing tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    apache2-utils \
    siege \
    && rm -rf /var/lib/apt/lists/*

# Install hey (load testing tool)
RUN wget https://hey-release.s3.us-east-2.amazonaws.com/hey_linux_amd64 \
    && chmod +x hey_linux_amd64 \
    && mv hey_linux_amd64 /usr/local/bin/hey

# Install vegeta (load testing tool)
RUN wget https://github.com/tsenart/vegeta/releases/download/v12.8.4/vegeta_12.8.4_linux_amd64.tar.gz \
    && tar -xzf vegeta_12.8.4_linux_amd64.tar.gz \
    && mv vegeta /usr/local/bin/ \
    && rm vegeta_12.8.4_linux_amd64.tar.gz

# Install k6 (load testing tool)
RUN gpg -k && gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69 \
    && echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | tee /etc/apt/sources.list.d/k6.list \
    && apt-get update \
    && apt-get install -y k6 \
    && rm -rf /var/lib/apt/lists/*

# Copy performance test scripts
COPY --chown=goat:goat scripts/performance-tests /app/scripts/performance-tests

# Switch back to non-root user
USER goat

# Run performance tests
CMD ["k6", "run", "/app/scripts/performance-tests/load-test.js"]

# ===========================================
# ADDITIONAL FILES NEEDED
# ===========================================

# docker-entrypoint.sh (create this file)
"""
#!/bin/bash
set -e

# Function to wait for database
wait_for_db() {
    echo "Waiting for database to be ready..."
    until PGPASSWORD=\${POSTGRES_PASSWORD} psql -h "\${POSTGRES_HOST}" -U "\${POSTGRES_USER}" -d "\${POSTGRES_DB}" -c '\q' 2>/dev/null; do
        echo "Database is unavailable - sleeping"
        sleep 1
    done
    echo "Database is ready!"
}

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis to be ready..."
    until redis-cli -h "\${REDIS_HOST}" -p "\${REDIS_PORT}" -a "\${REDIS_PASSWORD}" ping 2>/dev/null | grep -q "PONG"; do
        echo "Redis is unavailable - sleeping"
        sleep 1
    done
    echo "Redis is ready!"
}

# Run migrations if needed
run_migrations() {
    if [ "\${RUN_MIGRATIONS}" = "true" ]; then
        echo "Running database migrations..."
        alembic upgrade head
        echo "Migrations completed!"
    fi
}

# Run database seeding if needed
run_seeding() {
    if [ "\${RUN_SEEDING}" = "true" ]; then
        echo "Seeding database..."
        python -m src.cli seed
        echo "Seeding completed!"
    fi
}

# Set default environment variables
export POSTGRES_HOST=\${POSTGRES_HOST:-postgres}
export POSTGRES_PORT=\${POSTGRES_PORT:-5432}
export POSTGRES_DB=\${POSTGRES_DB:-goat_prediction}
export POSTGRES_USER=\${POSTGRES_USER:-goat_admin}
export POSTGRES_PASSWORD=\${POSTGRES_PASSWORD:-}
export REDIS_HOST=\${REDIS_HOST:-redis}
export REDIS_PORT=\${REDIS_PORT:-6379}
export REDIS_PASSWORD=\${REDIS_PASSWORD:-}
export RUN_MIGRATIONS=\${RUN_MIGRATIONS:-false}
export RUN_SEEDING=\${RUN_SEEDING:-false}

# Wait for dependencies if needed
if [ "\${WAIT_FOR_DB}" = "true" ]; then
    wait_for_db
fi

if [ "\${WAIT_FOR_REDIS}" = "true" ]; then
    wait_for_redis
fi

# Run migrations and seeding
run_migrations
run_seeding

# Execute the main command
exec "\$@"
"""

# .dockerignore (create this file)
"""
# Docker ignore file for GOAT Prediction API Gateway

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
.mypy_cache/
.ruff_cache/

# Environment
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
lerna-debug.log*

# Coverage reports
coverage/
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Jupyter Notebook
.ipynb_checkpoints

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# PyCharm
.idea/

# VS Code
.vscode/

# macOS
.DS_Store

# Temporary files
tmp/
temp/

# Documentation
docs/_build/

# Docker
.dockerignore
Dockerfile
docker-compose.yml
.docker/

# Git
.git/
.gitignore
.gitattributes

# Security
secrets/
*.key
*.pem
*.crt

# Development
.devcontainer/

# Production excludes
*.md
*.txt
LICENSE
docker-compose.*.yml
docker-compose.*.yaml
test*
tests/
scripts/
examples/
benchmarks/

# Keep only necessary files for production
!src/
!pyproject.toml
!poetry.lock
!alembic.ini
!docker-entrypoint.sh
"""

# docker-compose.override.yml (for development)
"""
version: '3.8'

services:
  api-gateway:
    build:
      context: .
      target: development
    volumes:
      - .:/app
      - /app/venv
      - /app/.pytest_cache
      - /app/.mypy_cache
    environment:
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
      - RELOAD=true
      - PYTHONPATH=/app
    ports:
      - "8000:8000"
      - "5678:5678"  # For debugpy
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    environment:
      - POSTGRES_DB=goat_prediction_dev
      - POSTGRES_USER=goat_admin
      - POSTGRES_PASSWORD=dev_password
    ports:
      - "5432:5432"

  redis:
    ports:
      - "6379:6379"

  redis-commander:
    ports:
      - "8081:8081"

  pgadmin:
    ports:
      - "8082:80"

  jaeger:
    ports:
      - "16686:16686"

  grafana:
    ports:
      - "3000:3000"

  prometheus:
    ports:
      - "9090:9090"

  loki:
    ports:
      - "3100:3100"

  portainer:
    ports:
      - "9000:9000"
      - "9443:9443"

  mailhog:
    ports:
      - "1025:1025"
      - "8025:8025"

  minio:
    ports:
      - "9000:9000"
      - "9001:9001"

  elasticsearch:
    ports:
      - "9200:9200"

  kibana:
    ports:
      - "5601:5601"
"""

# docker-compose.prod.yml (for production)
"""
version: '3.8'

services:
  api-gateway:
    build:
      context: .
      target: production
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - RELOAD=false
      - WAIT_FOR_DB=true
      - WAIT_FOR_REDIS=true
      - RUN_MIGRATIONS=true
      - RUN_SEEDING=false
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 30s
        order: start-first
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 3
        window: 120s
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    volumes:
      - redis_data:/data

  prometheus:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    volumes:
      - prometheus_data:/prometheus

  grafana:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    volumes:
      - grafana_data:/var/lib/grafana

  nginx:
    image: nginx:alpine
    container_name: goat-nginx-prod
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - api-gateway
    networks:
      - goat-network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  certbot:
    image: certbot/certbot:latest
    container_name: goat-certbot
    volumes:
      - ./ssl:/etc/letsencrypt
      - ./logs/letsencrypt:/var/log/letsencrypt
    command: certonly --webroot -w /var/www/certbot --email admin@goat-prediction.com -d goat-prediction.com --agree-tos --no-eff-email --force-renewal
    networks:
      - goat-network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local

networks:
  goat-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/16
          gateway: 172.30.0.1
"""
