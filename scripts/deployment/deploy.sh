#!/bin/bash

# 🚀 GOAT-PREDICTION ULTIMATE - DEPLOYMENT SCRIPT
# Version: 2.0.0
# Description: Complete deployment script for GOAT-PREDICTION Ultimate platform
# Author: GOAT-PREDICTION Team
# Date: $(date)

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Environment variables with defaults
ENVIRONMENT=${ENVIRONMENT:-"production"}
VERSION=${VERSION:-"$(date +%Y%m%d%H%M%S)"}
REGISTRY=${REGISTRY:-"ghcr.io"}
IMAGE_PREFIX=${IMAGE_PREFIX:-"goat-prediction"}
KUBE_NAMESPACE=${KUBE_NAMESPACE:-"goat-prediction-$ENVIRONMENT"}
KUBE_CONTEXT=${KUBE_CONTEXT:-""}
AWS_REGION=${AWS_REGION:-"us-east-1"}
DB_BACKUP=${DB_BACKUP:-"true"}
ROLLBACK_ON_ERROR=${ROLLBACK_ON_ERROR:-"true"}
DEPLOYMENT_TIMEOUT=${DEPLOYMENT_TIMEOUT:-600}
HEALTH_CHECK_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-300}
CONCURRENCY=${CONCURRENCY:-"3"}
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
EMAIL_NOTIFICATIONS=${EMAIL_NOTIFICATIONS:-"false"}

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$ROOT_DIR/.backups/deployments"
LOG_DIR="$ROOT_DIR/.logs/deployment"
CONFIG_DIR="$ROOT_DIR/.config"
SECRETS_DIR="$ROOT_DIR/.secrets"

# Files
DEPLOYMENT_LOG="$LOG_DIR/deployment_$(date +%Y%m%d_%H%M%S).log"
ERROR_LOG="$LOG_DIR/errors_$(date +%Y%m%d_%H%M%S).log"
LOCK_FILE="/tmp/goat-deployment.lock"
STATE_FILE="$LOG_DIR/deployment_state.json"

# =============================================================================
# FUNCTIONS
# =============================================================================

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$DEPLOYMENT_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$DEPLOYMENT_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$DEPLOYMENT_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$DEPLOYMENT_LOG" "$ERROR_LOG"
}

log_step() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${GREEN}STEP: $1${NC}"
    echo -e "${BLUE}========================================${NC}\n" | tee -a "$DEPLOYMENT_LOG"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites"
    
    local missing_tools=()
    
    # Check required tools
    declare -A tools=(
        ["docker"]="Docker"
        ["docker-compose"]="Docker Compose"
        ["kubectl"]="Kubernetes CLI"
        ["helm"]="Helm"
        ["aws"]="AWS CLI"
        ["terraform"]="Terraform"
        ["jq"]="jq"
        ["curl"]="curl"
        ["git"]="Git"
    )
    
    for cmd in "${!tools[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_tools+=("${tools[$cmd]} ($cmd)")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools:"
        for tool in "${missing_tools[@]}"; do
            log_error "  - $tool"
        done
        exit 1
    fi
    
    log_success "All prerequisites met"
}

# Initialize directories
init_directories() {
    log_step "Initializing directories"
    
    mkdir -p "$BACKUP_DIR" "$LOG_DIR" "$CONFIG_DIR" "$SECRETS_DIR"
    mkdir -p "$BACKUP_DIR/database" "$BACKUP_DIR/config" "$BACKUP_DIR/models"
    
    log_success "Directories initialized"
}

# Check lock file
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_error "Deployment is already running (PID: $pid)"
            exit 1
        else
            log_warning "Stale lock file found, removing..."
            rm -f "$LOCK_FILE"
        fi
    fi
    
    echo $$ > "$LOCK_FILE"
    trap 'cleanup_lock' EXIT
}

cleanup_lock() {
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
    fi
}

# Load configuration
load_config() {
    log_step "Loading configuration"
    
    # Load environment specific config
    local env_file="$ROOT_DIR/.env.$ENVIRONMENT"
    if [ -f "$env_file" ]; then
        log_info "Loading environment variables from $env_file"
        set -a
        source "$env_file"
        set +a
    else
        log_warning "Environment file $env_file not found"
    fi
    
    # Load deployment config
    local deploy_config="$CONFIG_DIR/deployment.yaml"
    if [ -f "$deploy_config" ]; then
        log_info "Loading deployment configuration"
        export DEPLOYMENT_CONFIG=$(yq eval -o=json "$deploy_config" 2>/dev/null || echo "{}")
    fi
    
    # Validate required variables
    local required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "SUPABASE_URL"
        "SUPABASE_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_warning "Variable $var is not set"
        fi
    done
    
    log_success "Configuration loaded"
}

# Backup current deployment
backup_deployment() {
    if [ "$DB_BACKUP" != "true" ]; then
        log_info "Skipping backup (DB_BACKUP=false)"
        return 0
    fi
    
    log_step "Creating backup of current deployment"
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup database
    log_info "Backing up database..."
    if backup_database "$backup_path/database"; then
        log_success "Database backup created"
    else
        log_error "Failed to backup database"
        return 1
    fi
    
    # Backup configuration
    log_info "Backing up configuration..."
    cp -r "$CONFIG_DIR" "$backup_path/config/"
    cp -r "$ROOT_DIR/.env"* "$backup_path/config/"
    log_success "Configuration backed up"
    
    # Backup models
    log_info "Backing up ML models..."
    if [ -d "$ROOT_DIR/backend/prediction-engine/models" ]; then
        cp -r "$ROOT_DIR/backend/prediction-engine/models" "$backup_path/models/"
        log_success "Models backed up"
    fi
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
  "timestamp": "$backup_timestamp",
  "environment": "$ENVIRONMENT",
  "version": "$VERSION",
  "backup_type": "full",
  "components": ["database", "config", "models"],
  "size": "$(du -sh "$backup_path" | cut -f1)"
}
EOF
    
    log_success "Backup completed: $backup_path"
}

backup_database() {
    local backup_dir=$1
    mkdir -p "$backup_dir"
    
    # Backup PostgreSQL
    if [ -n "${DATABASE_URL:-}" ]; then
        log_info "Backing up PostgreSQL..."
        PGPASSWORD=$(echo "$DATABASE_URL" | grep -oP 'password=\K[^&]*' || echo "") \
        pg_dump "$DATABASE_URL" > "$backup_dir/database.sql" 2>> "$ERROR_LOG"
        
        if [ $? -eq 0 ]; then
            gzip "$backup_dir/database.sql"
            log_success "PostgreSQL backup completed"
        else
            log_error "PostgreSQL backup failed"
            return 1
        fi
    fi
    
    # Backup Redis
    if [ -n "${REDIS_URL:-}" ]; then
        log_info "Backing up Redis..."
        redis-cli -u "$REDIS_URL" --rdb "$backup_dir/dump.rdb" 2>> "$ERROR_LOG"
        
        if [ $? -eq 0 ]; then
            log_success "Redis backup completed"
        else
            log_warning "Redis backup failed or not available"
        fi
    fi
    
    return 0
}

# Build Docker images
build_images() {
    log_step "Building Docker images"
    
    local images=(
        "api-gateway"
        "prediction-engine"
        "frontend-web-app"
        "data-pipeline"
        "ml-models"
    )
    
    local build_errors=0
    
    for image in "${images[@]}"; do
        log_info "Building $image..."
        
        local dockerfile=""
        local context=""
        
        case $image in
            "api-gateway")
                dockerfile="$ROOT_DIR/backend/api-gateway/Dockerfile"
                context="$ROOT_DIR/backend/api-gateway"
                ;;
            "prediction-engine")
                dockerfile="$ROOT_DIR/backend/prediction-engine/Dockerfile"
                context="$ROOT_DIR/backend/prediction-engine"
                ;;
            "frontend-web-app")
                dockerfile="$ROOT_DIR/frontend/web-app/Dockerfile"
                context="$ROOT_DIR/frontend/web-app"
                ;;
            "data-pipeline")
                dockerfile="$ROOT_DIR/data-pipeline/Dockerfile"
                context="$ROOT_DIR/data-pipeline"
                ;;
            "ml-models")
                dockerfile="$ROOT_DIR/mlops/serving/Dockerfile"
                context="$ROOT_DIR/mlops"
                ;;
        esac
        
        if [ ! -f "$dockerfile" ]; then
            log_warning "Dockerfile not found for $image, skipping..."
            continue
        fi
        
        # Build with cache
        if docker build \
            -f "$dockerfile" \
            -t "$REGISTRY/$IMAGE_PREFIX/$image:$VERSION" \
            -t "$REGISTRY/$IMAGE_PREFIX/$image:latest" \
            --build-arg ENVIRONMENT="$ENVIRONMENT" \
            --build-arg VERSION="$VERSION" \
            --cache-from "$REGISTRY/$IMAGE_PREFIX/$image:latest" \
            "$context" >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"; then
            
            log_success "Built $image:$VERSION"
        else
            log_error "Failed to build $image"
            build_errors=$((build_errors + 1))
        fi
    done
    
    if [ $build_errors -gt 0 ]; then
        log_error "Failed to build $build_errors images"
        return 1
    fi
    
    log_success "All images built successfully"
}

# Push images to registry
push_images() {
    log_step "Pushing images to registry"
    
    # Login to registry
    log_info "Logging into registry $REGISTRY..."
    
    if [ "$REGISTRY" = "ghcr.io" ]; then
        echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin 2>> "$ERROR_LOG"
    elif [ "$REGISTRY" = "docker.io" ]; then
        echo "$DOCKER_PASSWORD" | docker login docker.io -u "$DOCKER_USERNAME" --password-stdin 2>> "$ERROR_LOG"
    elif [[ "$REGISTRY" =~ .*amazonaws\.com ]]; then
        aws ecr get-login-password --region "$AWS_REGION" | \
            docker login --username AWS --password-stdin "$REGISTRY" 2>> "$ERROR_LOG"
    fi
    
    if [ $? -ne 0 ]; then
        log_error "Failed to login to registry"
        return 1
    fi
    
    # Push images
    local images=(
        "api-gateway"
        "prediction-engine"
        "frontend-web-app"
        "data-pipeline"
        "ml-models"
    )
    
    local push_errors=0
    
    for image in "${images[@]}"; do
        log_info "Pushing $image..."
        
        for tag in "$VERSION" "latest"; do
            if docker push "$REGISTRY/$IMAGE_PREFIX/$image:$tag" >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"; then
                log_success "Pushed $image:$tag"
            else
                log_error "Failed to push $image:$tag"
                push_errors=$((push_errors + 1))
            fi
        done
    done
    
    if [ $push_errors -gt 0 ]; then
        log_error "Failed to push $push_errors images"
        return 1
    fi
    
    log_success "All images pushed successfully"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log_step "Deploying to Kubernetes"
    
    # Set kubectl context if specified
    if [ -n "$KUBE_CONTEXT" ]; then
        kubectl config use-context "$KUBE_CONTEXT" >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
        if [ $? -ne 0 ]; then
            log_error "Failed to switch kubectl context"
            return 1
        fi
    fi
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$KUBE_NAMESPACE" > /dev/null 2>&1; then
        log_info "Creating namespace $KUBE_NAMESPACE..."
        kubectl create namespace "$KUBE_NAMESPACE" >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
    fi
    
    # Apply secrets
    deploy_secrets
    
    # Apply configmaps
    deploy_configmaps
    
    # Deploy applications
    deploy_applications
    
    # Wait for deployment
    wait_for_deployment
    
    log_success "Kubernetes deployment completed"
}

deploy_secrets() {
    log_info "Deploying secrets..."
    
    # Create secret from .env file
    if [ -f "$ROOT_DIR/.env.$ENVIRONMENT" ]; then
        kubectl create secret generic app-secrets \
            --from-file=".env=$ROOT_DIR/.env.$ENVIRONMENT" \
            --namespace "$KUBE_NAMESPACE" \
            --dry-run=client -o yaml | \
            kubectl apply -f - >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
    fi
    
    # Create registry secret
    if [ -n "${REGISTRY_PASSWORD:-}" ]; then
        kubectl create secret docker-registry registry-credentials \
            --docker-server="$REGISTRY" \
            --docker-username="$REGISTRY_USERNAME" \
            --docker-password="$REGISTRY_PASSWORD" \
            --docker-email="$REGISTRY_EMAIL" \
            --namespace "$KUBE_NAMESPACE" \
            --dry-run=client -o yaml | \
            kubectl apply -f - >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
    fi
    
    log_success "Secrets deployed"
}

deploy_configmaps() {
    log_info "Deploying configmaps..."
    
    # Deploy all configmaps from infrastructure/kubernetes/configmaps
    local configmap_dir="$ROOT_DIR/infrastructure/kubernetes/configmaps"
    if [ -d "$configmap_dir" ]; then
        for config in "$configmap_dir"/*.yaml; do
            if [ -f "$config" ]; then
                # Update namespace in configmap
                yq eval ".metadata.namespace = \"$KUBE_NAMESPACE\"" "$config" | \
                    kubectl apply -f - >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
                
                if [ $? -eq 0 ]; then
                    log_success "Applied configmap: $(basename "$config")"
                else
                    log_error "Failed to apply configmap: $(basename "$config")"
                fi
            fi
        done
    fi
    
    log_success "Configmaps deployed"
}

deploy_applications() {
    log_info "Deploying applications..."
    
    # Update image versions in deployments
    update_deployment_images
    
    # Deploy in order
    local deployments=(
        "database"
        "redis"
        "message-queue"
        "api-gateway"
        "prediction-engine"
        "frontend"
        "data-pipeline"
        "monitoring"
    )
    
    for deploy in "${deployments[@]}"; do
        log_info "Deploying $deploy..."
        
        local deploy_file="$ROOT_DIR/infrastructure/kubernetes/deployments/$deploy.yaml"
        if [ -f "$deploy_file" ]; then
            # Update namespace and image version
            yq eval "
                .metadata.namespace = \"$KUBE_NAMESPACE\" |
                .spec.template.spec.containers[].image |= sub(\":latest\", \":$VERSION\")
            " "$deploy_file" | \
                kubectl apply -f - >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
            
            if [ $? -eq 0 ]; then
                log_success "Deployed $deploy"
            else
                log_error "Failed to deploy $deploy"
            fi
        else
            log_warning "Deployment file not found: $deploy_file"
        fi
    done
}

update_deployment_images() {
    log_info "Updating deployment images to version $VERSION"
    
    # Create kustomization file for version updates
    cat > "$ROOT_DIR/infrastructure/kubernetes/kustomization.yaml" << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: $KUBE_NAMESPACE
resources:
  - deployments/api-gateway.yaml
  - deployments/prediction-engine.yaml
  - deployments/frontend.yaml
  - deployments/data-pipeline.yaml
  - deployments/ml-models.yaml
images:
  - name: $REGISTRY/$IMAGE_PREFIX/api-gateway
    newTag: $VERSION
  - name: $REGISTRY/$IMAGE_PREFIX/prediction-engine
    newTag: $VERSION
  - name: $REGISTRY/$IMAGE_PREFIX/frontend-web-app
    newTag: $VERSION
  - name: $REGISTRY/$IMAGE_PREFIX/data-pipeline
    newTag: $VERSION
  - name: $REGISTRY/$IMAGE_PREFIX/ml-models
    newTag: $VERSION
EOF
}

wait_for_deployment() {
    log_info "Waiting for deployments to be ready (timeout: ${DEPLOYMENT_TIMEOUT}s)..."
    
    local start_time=$(date +%s)
    local deployments=(
        "api-gateway"
        "prediction-engine"
        "frontend"
    )
    
    for deploy in "${deployments[@]}"; do
        log_info "Checking deployment/$deploy..."
        
        while true; do
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))
            
            if [ $elapsed -gt $DEPLOYMENT_TIMEOUT ]; then
                log_error "Timeout waiting for $deploy to be ready"
                return 1
            fi
            
            if kubectl rollout status "deployment/$deploy" \
                --namespace "$KUBE_NAMESPACE" \
                --timeout=30s >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"; then
                log_success "$deploy is ready"
                break
            else
                log_info "$deploy not ready yet, waiting..."
                sleep 10
            fi
        done
    done
    
    log_success "All deployments are ready"
}

# Run database migrations
run_migrations() {
    log_step "Running database migrations"
    
    log_info "Running Alembic migrations..."
    
    # Get database pod
    local db_pod=$(kubectl get pods --namespace "$KUBE_NAMESPACE" \
        -l app=postgres \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [ -n "$db_pod" ]; then
        # Run migrations inside pod
        kubectl exec "$db_pod" --namespace "$KUBE_NAMESPACE" -- \
            alembic upgrade head >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
        
        if [ $? -eq 0 ]; then
            log_success "Database migrations completed"
        else
            log_error "Database migrations failed"
            return 1
        fi
    else
        log_warning "Database pod not found, skipping migrations"
    fi
    
    log_success "Migrations completed"
}

# Run health checks
run_health_checks() {
    log_step "Running health checks"
    
    local services=(
        "api-gateway"
        "prediction-engine"
        "frontend"
    )
    
    local health_errors=0
    
    for service in "${services[@]}"; do
        log_info "Checking health of $service..."
        
        local endpoint=""
        case $service in
            "api-gateway")
                endpoint="http://api.goat-prediction.local/health"
                ;;
            "prediction-engine")
                endpoint="http://prediction.goat-prediction.local/health"
                ;;
            "frontend")
                endpoint="http://app.goat-prediction.local/health"
                ;;
        esac
        
        if [ -n "$endpoint" ]; then
            local start_time=$(date +%s)
            local healthy=false
            
            while [ "$healthy" = false ]; do
                local current_time=$(date +%s)
                local elapsed=$((current_time - start_time))
                
                if [ $elapsed -gt $HEALTH_CHECK_TIMEOUT ]; then
                    log_error "Health check timeout for $service"
                    health_errors=$((health_errors + 1))
                    break
                fi
                
                if curl -s -f "$endpoint" > /dev/null 2>&1; then
                    log_success "$service is healthy"
                    healthy=true
                else
                    log_info "$service not responding, retrying..."
                    sleep 5
                fi
            done
        fi
    done
    
    if [ $health_errors -gt 0 ]; then
        log_error "Health checks failed for $health_errors services"
        return 1
    fi
    
    log_success "All health checks passed"
}

# Run smoke tests
run_smoke_tests() {
    log_step "Running smoke tests"
    
    log_info "Testing API endpoints..."
    
    # Test prediction endpoint
    if curl -s -X POST "http://api.goat-prediction.local/api/v1/predictions" \
        -H "Content-Type: application/json" \
        -d '{"sport": "football", "match_id": "test"}' \
        --max-time 30 >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"; then
        log_success "Prediction API is working"
    else
        log_error "Prediction API test failed"
        return 1
    fi
    
    # Test health endpoint
    if curl -s -f "http://api.goat-prediction.local/health" >> "$DEPLOYMENT_LOG" 2>&1; then
        log_success "Health endpoint is working"
    else
        log_error "Health endpoint test failed"
        return 1
    fi
    
    log_success "Smoke tests completed"
}

# Update deployment state
update_deployment_state() {
    local state=$1
    local message=${2:-""}
    
    cat > "$STATE_FILE" << EOF
{
  "environment": "$ENVIRONMENT",
  "version": "$VERSION",
  "state": "$state",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "message": "$message",
  "deployment_id": "$(uuidgen || echo "unknown")"
}
EOF
}

# Send notifications
send_notification() {
    local type=$1
    local message=$2
    
    # Slack notification
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local slack_payload=$(cat << EOF
{
  "text": "*GOAT-PREDICTION Deployment - $ENVIRONMENT*",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "🚀 GOAT-PREDICTION Deployment"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Environment:*\n$ENVIRONMENT"
        },
        {
          "type": "mrkdwn",
          "text": "*Version:*\n$VERSION"
        },
        {
          "type": "mrkdwn",
          "text": "*Status:*\n$type"
        },
        {
          "type": "mrkdwn",
          "text": "*Time:*\n$(date)"
        }
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "$message"
      }
    }
  ]
}
EOF
        )
        
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$slack_payload" >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG" || true
    fi
    
    # Email notification (simplified)
    if [ "$EMAIL_NOTIFICATIONS" = "true" ] && [ -n "${EMAIL_RECIPIENTS:-}" ]; then
        local subject="GOAT-PREDICTION Deployment $type - $ENVIRONMENT"
        echo -e "Deployment $type\n\nEnvironment: $ENVIRONMENT\nVersion: $VERSION\nTime: $(date)\n\n$message" | \
            mail -s "$subject" "$EMAIL_RECIPIENTS" 2>> "$ERROR_LOG" || true
    fi
}

# Rollback deployment
rollback_deployment() {
    log_step "Rolling back deployment"
    
    local rollback_version=${1:-"previous"}
    
    log_info "Rolling back to version: $rollback_version"
    
    # Get previous deployment
    if [ "$rollback_version" = "previous" ]; then
        rollback_version=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "*" | \
            sort -r | head -2 | tail -1 | xargs basename)
    fi
    
    if [ -z "$rollback_version" ]; then
        log_error "No previous version found for rollback"
        return 1
    fi
    
    local backup_path="$BACKUP_DIR/$rollback_version"
    
    if [ ! -d "$backup_path" ]; then
        log_error "Backup not found: $backup_path"
        return 1
    fi
    
    # Restore database
    log_info "Restoring database from backup..."
    if restore_database "$backup_path/database"; then
        log_success "Database restored"
    else
        log_error "Failed to restore database"
        return 1
    fi
    
    # Rollback Kubernetes deployments
    log_info "Rolling back Kubernetes deployments..."
    
    # Scale down current deployment
    kubectl scale deployment --namespace "$KUBE_NAMESPACE" --replicas=0 --all >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
    
    # Apply previous deployment configuration
    if [ -f "$backup_path/config/k8s-backup.yaml" ]; then
        kubectl apply -f "$backup_path/config/k8s-backup.yaml" >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
    fi
    
    log_success "Rollback completed to version: $rollback_version"
    send_notification "ROLLBACK" "Deployment rolled back to version $rollback_version"
}

restore_database() {
    local backup_dir=$1
    
    # Restore PostgreSQL
    if [ -f "$backup_dir/database.sql.gz" ]; then
        log_info "Restoring PostgreSQL..."
        gunzip -c "$backup_dir/database.sql.gz" | \
            psql "$DATABASE_URL" >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
        
        if [ $? -ne 0 ]; then
            log_error "Failed to restore PostgreSQL"
            return 1
        fi
    fi
    
    # Restore Redis
    if [ -f "$backup_dir/dump.rdb" ]; then
        log_info "Restoring Redis..."
        redis-cli -u "$REDIS_URL" --rdb "$backup_dir/dump.rdb" >> "$DEPLOYMENT_LOG" 2>> "$ERROR_LOG"
    fi
    
    return 0
}

# Cleanup old deployments
cleanup_old_deployments() {
    log_step "Cleaning up old deployments"
    
    # Keep last 5 backups
    local backups_to_keep=5
    local backup_count=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "2*" | wc -l)
    
    if [ "$backup_count" -gt "$backups_to_keep" ]; then
        local backups_to_delete=$((backup_count - backups_to_keep))
        log_info "Removing $backups_to_delete old backups"
        
        find "$BACKUP_DIR" -maxdepth 1 -type d -name "2*" | \
            sort | head -n "$backups_to_delete" | \
            xargs rm -rf
    fi
    
    # Clean old logs (keep 30 days)
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete
    find "$LOG_DIR" -name "*.json" -mtime +30 -delete
    
    log_success "Cleanup completed"
}

# Main deployment function
deploy() {
    log_step "Starting GOAT-PREDICTION Ultimate Deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    log_info "Registry: $REGISTRY"
    log_info "Namespace: $KUBE_NAMESPACE"
    
    # Start timer
    local start_time=$(date +%s)
    
    # Update state
    update_deployment_state "STARTED" "Deployment started"
    send_notification "STARTED" "Deployment started for version $VERSION"
    
    # Execute deployment steps
    local steps=(
        "check_prerequisites"
        "init_directories"
        "check_lock"
        "load_config"
        "backup_deployment"
        "build_images"
        "push_images"
        "deploy_kubernetes"
        "run_migrations"
        "run_health_checks"
        "run_smoke_tests"
        "cleanup_old_deployments"
    )
    
    local failed_step=""
    
    for step in "${steps[@]}"; do
        log_info "Executing step: $step"
        
        if $step; then
            log_success "Step completed: $step"
        else
            log_error "Step failed: $step"
            failed_step="$step"
            
            # Rollback if enabled
            if [ "$ROLLBACK_ON_ERROR" = "true" ]; then
                log_warning "Rolling back due to failure in step: $step"
                rollback_deployment
            fi
            
            break
        fi
    done
    
    # Calculate duration
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Final state
    if [ -z "$failed_step" ]; then
        update_deployment_state "SUCCESS" "Deployment completed successfully in ${duration}s"
        send_notification "SUCCESS" "Deployment $VERSION completed successfully in ${duration}s"
        log_success "🚀 Deployment completed successfully in ${duration} seconds!"
        return 0
    else
        update_deployment_state "FAILED" "Deployment failed at step: $failed_step"
        send_notification "FAILED" "Deployment $VERSION failed at step: $failed_step"
        log_error "💥 Deployment failed at step: $failed_step"
        return 1
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            --registry)
                REGISTRY="$2"
                shift 2
                ;;
            --namespace)
                KUBE_NAMESPACE="$2"
                shift 2
                ;;
            --context)
                KUBE_CONTEXT="$2"
                shift 2
                ;;
            --no-backup)
                DB_BACKUP="false"
                shift
                ;;
            --no-rollback)
                ROLLBACK_ON_ERROR="false"
                shift
                ;;
            --slack-webhook)
                SLACK_WEBHOOK_URL="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Create log file
    mkdir -p "$(dirname "$DEPLOYMENT_LOG")"
    exec > >(tee -a "$DEPLOYMENT_LOG")
    exec 2> >(tee -a "$ERROR_LOG")
    
    # Show banner
    show_banner
    
    # Run deployment
    if deploy; then
        exit 0
    else
        exit 1
    fi
}

show_banner() {
    cat << "EOF"

    ██████╗  ██████╗  █████╗ ████████╗    ██████╗ ██████╗ ███████╗██████╗ ██╗ ██████╗████████╗██╗ ██████╗ ███╗   ██╗
    ██╔════╝ ██╔═══██╗██╔══██╗╚══██╔══╝    ██╔══██╗██╔══██╗██╔════╝██╔══██╗██║██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██╗
    ██║  ███╗██║   ██║███████║   ██║       ██████╔╝██████╔╝█████╗  ██║  ██║██║██║        ██║   ██║██║   ██║██╔██╗ ██║
    ██║   ██║██║   ██║██╔══██║   ██║       ██╔═══╝ ██╔══██╗██╔══╝  ██║  ██║██║██║        ██║   ██║██║   ██║██║╚██╗██║
    ╚██████╔╝╚██████╔╝██║  ██║   ██║       ██║     ██║  ██║███████╗██████╔╝██║╚██████╗   ██║   ██║╚██████╔╝██║ ╚████║
    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝       ╚═╝     ╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝ ╚═════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
    
    🚀 GOAT-PREDICTION ULTIMATE - DEPLOYMENT SCRIPT v2.0.0
    =============================================================================
    
EOF
}

show_help() {
    cat << EOF
GOAT-PREDICTION Ultimate Deployment Script

Usage: $0 [OPTIONS]

Options:
  -e, --environment ENV    Deployment environment (default: production)
  -v, --version VERSION    Deployment version (default: timestamp)
  --registry REGISTRY      Docker registry URL (default: ghcr.io)
  --namespace NAMESPACE    Kubernetes namespace (default: goat-prediction-\$ENVIRONMENT)
  --context CONTEXT        kubectl context to use
  --no-backup              Skip database backup
  --no-rollback           Disable automatic rollback on error
  --slack-webhook URL     Slack webhook URL for notifications
  --help                  Show this help message

Examples:
  $0 --environment staging --version 2.1.0
  $0 --environment production --slack-webhook https://hooks.slack.com/...

Environment Variables:
  DATABASE_URL           PostgreSQL connection string
  REDIS_URL              Redis connection string
  SUPABASE_URL           Supabase URL
  SUPABASE_KEY           Supabase API key
  GITHUB_TOKEN           GitHub token for container registry
  AWS_ACCESS_KEY_ID      AWS access key for ECR
  AWS_SECRET_ACCESS_KEY  AWS secret key for ECR

EOF
}

# =============================================================================
# EXECUTE
# =============================================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
