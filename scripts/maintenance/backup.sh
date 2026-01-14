#!/bin/bash

# 🐐 GOAT-PREDICTION ULTIMATE - BACKUP SCRIPT
# Version: 2.0.0
# Description: Comprehensive backup solution for GOAT-PREDICTION Ultimate platform
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
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Environment variables with defaults
ENVIRONMENT=${ENVIRONMENT:-"production"}
BACKUP_TYPE=${BACKUP_TYPE:-"full"}  # full, incremental, differential
COMPRESSION=${COMPRESSION:-"gzip"}  # gzip, bzip2, xz, none
ENCRYPTION=${ENCRYPTION:-"true"}
ENCRYPTION_KEY_FILE=${ENCRYPTION_KEY_FILE:-""}
RETENTION_DAYS=${RETENTION_DAYS:-30}
RETENTION_WEEKS=${RETENTION_WEEKS:-4}
RETENTION_MONTHS=${RETENTION_MONTHS:-12}
MAX_BACKUP_SIZE=${MAX_BACKUP_SIZE:-"100G"}
UPLOAD_TO_S3=${UPLOAD_TO_S3:-"false"}
S3_BUCKET=${S3_BUCKET:-"goat-prediction-backups"}
S3_REGION=${S3_REGION:-"us-east-1"}
VERIFY_BACKUP=${VERIFY_BACKUP:-"true"}
SEND_NOTIFICATIONS=${SEND_NOTIFICATIONS:-"true"}
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
EMAIL_RECIPIENTS=${EMAIL_RECIPIENTS:-""}
BACKUP_ID=$(date +%Y%m%d_%H%M%S)_${BACKUP_TYPE}_${ENVIRONMENT}

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
BACKUP_ROOT="$ROOT_DIR/.backups"
BACKUP_DIR="$BACKUP_ROOT/$BACKUP_ID"
LOG_DIR="$ROOT_DIR/.logs/backup"
CONFIG_DIR="$ROOT_DIR/.config"
SECRETS_DIR="$ROOT_DIR/.secrets"
TEMP_DIR="/tmp/goat_backup_$BACKUP_ID"

# Files
BACKUP_LOG="$LOG_DIR/backup_${BACKUP_ID}.log"
ERROR_LOG="$LOG_DIR/error_${BACKUP_ID}.log"
MANIFEST_FILE="$BACKUP_DIR/manifest.json"
VERIFICATION_FILE="$BACKUP_DIR/verification.md5"
LOCK_FILE="/tmp/goat_backup.lock"
STATE_FILE="$LOG_DIR/backup_state_${BACKUP_ID}.json"
ENCRYPTION_KEY=""
DATABASE_URL=${DATABASE_URL:-""}
REDIS_URL=${REDIS_URL:-""}
SUPABASE_URL=${SUPABASE_URL:-""}
SUPABASE_KEY=${SUPABASE_KEY:-""}

# Components to backup
BACKUP_COMPONENTS=(
    "database"
    "redis"
    "supabase"
    "ml_models"
    "config"
    "secrets"
    "logs"
    "docker_volumes"
    "kubernetes"
    "terraform_state"
)

# =============================================================================
# FUNCTIONS
# =============================================================================

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$BACKUP_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$BACKUP_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$BACKUP_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$BACKUP_LOG" "$ERROR_LOG"
}

log_step() {
    echo -e "\n${PURPLE}========================================${NC}"
    echo -e "${CYAN}STEP: $1${NC}"
    echo -e "${PURPLE}========================================${NC}\n" | tee -a "$BACKUP_LOG"
}

# Banner display
show_banner() {
    clear
    cat << "EOF"

    ██████╗  ██████╗  █████╗ ████████╗    ██████╗  █████╗  ██████╗██╗  ██╗██╗   ██╗██████╗ 
    ██╔════╝ ██╔═══██╗██╔══██╗╚══██╔══╝    ██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██║   ██║██╔══██╗
    ██║  ███╗██║   ██║███████║   ██║       ██████╔╝███████║██║     █████╔╝ ██║   ██║██████╔╝
    ██║   ██║██║   ██║██╔══██║   ██║       ██╔══██╗██╔══██║██║     ██╔═██╗ ██║   ██║██╔═══╝ 
    ╚██████╔╝╚██████╔╝██║  ██║   ██║       ██████╔╝██║  ██║╚██████╗██║  ██╗╚██████╔╝██║     
    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝       ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     
    
    🐐 GOAT-PREDICTION ULTIMATE - BACKUP SYSTEM v2.0.0
    =============================================================================
    
EOF
    log_info "Starting backup process: $BACKUP_ID"
    log_info "Environment: $ENVIRONMENT | Type: $BACKUP_TYPE | Compression: $COMPRESSION"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites"
    
    local missing_tools=()
    
    # Check required tools
    declare -A tools=(
        ["pg_dump"]="PostgreSQL Client"
        ["redis-cli"]="Redis CLI"
        ["aws"]="AWS CLI (for S3 upload)"
        ["gpg"]="GNU Privacy Guard"
        ["jq"]="jq JSON processor"
        ["tar"]="tar archiver"
        ["gzip"]="gzip compression"
        ["bzip2"]="bzip2 compression"
        ["xz"]="xz compression"
        ["md5sum"]="md5 checksum"
        ["du"]="disk usage"
        ["curl"]="curl"
    )
    
    for cmd in "${!tools[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_tools+=("${tools[$cmd]} ($cmd)")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_warning "Missing optional tools:"
        for tool in "${missing_tools[@]}"; do
            log_warning "  - $tool"
        done
    fi
    
    # Check disk space
    local available_space=$(df -k "$BACKUP_ROOT" | tail -1 | awk '{print $4}')
    local min_space=$((10 * 1024 * 1024))  # 10GB minimum
    
    if [ "$available_space" -lt "$min_space" ]; then
        log_error "Insufficient disk space. Available: ${available_space}KB, Required: ${min_space}KB"
        return 1
    fi
    
    log_success "Prerequisites check passed"
}

# Initialize directories
init_directories() {
    log_step "Initializing directories"
    
    # Create main directories
    mkdir -p "$BACKUP_DIR" "$LOG_DIR" "$TEMP_DIR"
    mkdir -p "$BACKUP_DIR/database"
    mkdir -p "$BACKUP_DIR/redis"
    mkdir -p "$BACKUP_DIR/supabase"
    mkdir -p "$BACKUP_DIR/ml_models"
    mkdir -p "$BACKUP_DIR/config"
    mkdir -p "$BACKUP_DIR/secrets"
    mkdir -p "$BACKUP_DIR/logs"
    mkdir -p "$BACKUP_DIR/docker"
    mkdir -p "$BACKUP_DIR/kubernetes"
    mkdir -p "$BACKUP_DIR/terraform"
    
    # Set secure permissions
    chmod 700 "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR/secrets"
    
    log_success "Directories initialized: $BACKUP_DIR"
}

# Check lock file
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        local process_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
        
        if [ "$process_name" = "backup.sh" ] || [ "$process_name" = "bash" ]; then
            log_error "Backup is already running (PID: $pid)"
            send_notification "ERROR" "Backup failed: Already running (PID: $pid)"
            exit 1
        else
            log_warning "Stale lock file found, removing..."
            rm -f "$LOCK_FILE"
        fi
    fi
    
    echo $$ > "$LOCK_FILE"
    trap 'cleanup_lock' EXIT INT TERM
}

cleanup_lock() {
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        log_info "Lock file removed"
    fi
}

# Setup encryption
setup_encryption() {
    if [ "$ENCRYPTION" != "true" ]; then
        log_info "Encryption disabled"
        return 0
    fi
    
    log_step "Setting up encryption"
    
    # Generate or load encryption key
    if [ -n "$ENCRYPTION_KEY_FILE" ] && [ -f "$ENCRYPTION_KEY_FILE" ]; then
        ENCRYPTION_KEY=$(cat "$ENCRYPTION_KEY_FILE")
        log_info "Using encryption key from file: $ENCRYPTION_KEY_FILE"
    else
        ENCRYPTION_KEY=$(openssl rand -base64 32)
        local key_file="$SECRETS_DIR/backup_key_$(date +%Y%m%d).key"
        echo "$ENCRYPTION_KEY" > "$key_file"
        chmod 600 "$key_file"
        log_info "Generated new encryption key: $key_file"
    fi
    
    # Export key for subprocesses
    export ENCRYPTION_KEY
    
    log_success "Encryption setup complete"
}

# Update backup state
update_backup_state() {
    local state=$1
    local message=${2:-""}
    local component=${3:-"system"}
    
    cat > "$STATE_FILE" << EOF
{
  "backup_id": "$BACKUP_ID",
  "environment": "$ENVIRONMENT",
  "type": "$BACKUP_TYPE",
  "state": "$state",
  "component": "$component",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "message": "$message",
  "size_bytes": "$(get_directory_size "$BACKUP_DIR")"
}
EOF
}

# Get directory size
get_directory_size() {
    local dir=$1
    du -sb "$dir" 2>/dev/null | cut -f1 || echo "0"
}

# Backup database
backup_database() {
    log_step "Backing up database"
    
    if [ -z "$DATABASE_URL" ]; then
        log_warning "DATABASE_URL not set, skipping database backup"
        return 0
    fi
    
    local db_backup_dir="$BACKUP_DIR/database"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    # Extract database connection details
    local dbname=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/.*\/\([^?]*\).*/\1/p')
    local host=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:/]*\).*/\1/p')
    local port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\).*/\1/p')
    local user=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    local password=$(echo "$DATABASE_URL" | sed -n 's/.*:\([^@]*\)@.*/\1/p')
    
    log_info "Database: $dbname on $host:$port"
    
    # PostgreSQL backup
    log_info "Starting PostgreSQL backup..."
    
    # Set PGPASSWORD for pg_dump
    export PGPASSWORD="$password"
    
    # Full backup
    if [ "$BACKUP_TYPE" = "full" ]; then
        pg_dump -h "$host" -p "${port:-5432}" -U "$user" -d "$dbname" \
            --format=custom \
            --verbose \
            --no-owner \
            --no-acl \
            --clean \
            --if-exists \
            --file="$db_backup_dir/postgres_${timestamp}.dump" 2>> "$ERROR_LOG"
    else
        # Incremental backup (base backup + WAL files)
        pg_basebackup -h "$host" -p "${port:-5432}" -U "$user" -D "$db_backup_dir/base" \
            --format=tar \
            --gzip \
            --progress \
            --verbose 2>> "$ERROR_LOG"
    fi
    
    if [ $? -eq 0 ]; then
        local backup_size=$(du -h "$db_backup_dir" | tail -1 | cut -f1)
        log_success "Database backup completed: $backup_size"
        
        # Create database info file
        cat > "$db_backup_dir/info.json" << EOF
{
  "database": "postgresql",
  "name": "$dbname",
  "host": "$host",
  "port": "${port:-5432}",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$timestamp",
  "size": "$backup_size",
  "format": "custom",
  "version": "$(psql -h "$host" -p "${port:-5432}" -U "$user" -d "$dbname" -t -c "SELECT version();" 2>/dev/null | head -1)"
}
EOF
    else
        log_error "Database backup failed"
        return 1
    fi
    
    # Unset password
    unset PGPASSWORD
    
    return 0
}

# Backup Redis
backup_redis() {
    log_step "Backing up Redis"
    
    if [ -z "$REDIS_URL" ]; then
        log_warning "REDIS_URL not set, skipping Redis backup"
        return 0
    fi
    
    local redis_backup_dir="$BACKUP_DIR/redis"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    log_info "Redis URL: $REDIS_URL"
    
    # Save Redis data
    if redis-cli -u "$REDIS_URL" SAVE 2>> "$ERROR_LOG"; then
        # Find the dump.rdb file (usually in Redis data directory)
        local redis_dir=$(redis-cli -u "$REDIS_URL" CONFIG GET dir 2>/dev/null | tail -1)
        local dump_file="$redis_dir/dump.rdb"
        
        if [ -f "$dump_file" ]; then
            cp "$dump_file" "$redis_backup_dir/redis_${timestamp}.rdb"
            
            # Compress if needed
            if [ "$COMPRESSION" = "gzip" ]; then
                gzip "$redis_backup_dir/redis_${timestamp}.rdb"
            fi
            
            local backup_size=$(du -h "$redis_backup_dir" | tail -1 | cut -f1)
            log_success "Redis backup completed: $backup_size"
            
            # Create Redis info file
            cat > "$redis_backup_dir/info.json" << EOF
{
  "database": "redis",
  "url": "$REDIS_URL",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$timestamp",
  "size": "$backup_size",
  "version": "$(redis-cli -u "$REDIS_URL" INFO server 2>/dev/null | grep 'redis_version:' | cut -d: -f2)",
  "keys": "$(redis-cli -u "$REDIS_URL" DBSIZE 2>/dev/null)"
}
EOF
        else
            log_error "Redis dump file not found: $dump_file"
            return 1
        fi
    else
        log_error "Redis backup failed"
        return 1
    fi
    
    return 0
}

# Backup Supabase
backup_supabase() {
    log_step "Backing up Supabase"
    
    if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
        log_warning "SUPABASE_URL or SUPABASE_KEY not set, skipping Supabase backup"
        return 0
    fi
    
    local supabase_backup_dir="$BACKUP_DIR/supabase"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    log_info "Supabase URL: $SUPABASE_URL"
    
    # Backup Supabase tables using API
    local tables=("predictions" "users" "bets" "matches" "teams" "players")
    
    for table in "${tables[@]}"; do
        log_info "Backing up table: $table"
        
        curl -s -X GET \
            "$SUPABASE_URL/rest/v1/$table?select=*" \
            -H "apikey: $SUPABASE_KEY" \
            -H "Authorization: Bearer $SUPABASE_KEY" \
            -H "Content-Type: application/json" \
            -o "$supabase_backup_dir/${table}_${timestamp}.json" 2>> "$ERROR_LOG"
        
        if [ $? -eq 0 ]; then
            local file_size=$(du -h "$supabase_backup_dir/${table}_${timestamp}.json" | cut -f1)
            log_success "Table $table backed up: $file_size"
        else
            log_warning "Failed to backup table: $table"
        fi
    done
    
    # Create Supabase info file
    cat > "$supabase_backup_dir/info.json" << EOF
{
  "service": "supabase",
  "url": "$SUPABASE_URL",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$timestamp",
  "tables_backed_up": "${tables[*]}",
  "total_size": "$(du -sh "$supabase_backup_dir" | cut -f1)"
}
EOF
    
    log_success "Supabase backup completed"
    return 0
}

# Backup ML models
backup_ml_models() {
    log_step "Backing up ML models"
    
    local models_backup_dir="$BACKUP_DIR/ml_models"
    local models_source="$ROOT_DIR/backend/prediction-engine/models"
    
    if [ ! -d "$models_source" ]; then
        log_warning "ML models directory not found: $models_source"
        return 0
    fi
    
    log_info "Source: $models_source"
    
    # Backup all model files
    rsync -av --progress \
        --exclude="*.tmp" \
        --exclude="*.cache" \
        --exclude="__pycache__" \
        "$models_source/" "$models_backup_dir/" 2>> "$ERROR_LOG"
    
    if [ $? -eq 0 ]; then
        local model_count=$(find "$models_backup_dir" -name "*.joblib" -o -name "*.pkl" -o -name "*.h5" -o -name "*.pt" | wc -l)
        local backup_size=$(du -sh "$models_backup_dir" | cut -f1)
        
        log_success "ML models backup completed: $model_count models, $backup_size"
        
        # Create models manifest
        find "$models_backup_dir" -type f \( -name "*.joblib" -o -name "*.pkl" -o -name "*.h5" -o -name "*.pt" \) \
            -exec sh -c 'echo "  - $(basename "{}") ($(du -h "{}" | cut -f1))"' \; > "$models_backup_dir/manifest.txt"
        
        cat > "$models_backup_dir/info.json" << EOF
{
  "component": "ml_models",
  "source_directory": "$models_source",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$(date +%Y%m%d_%H%M%S)",
  "model_count": $model_count,
  "total_size": "$backup_size",
  "compression": "$COMPRESSION"
}
EOF
    else
        log_error "ML models backup failed"
        return 1
    fi
    
    return 0
}

# Backup configuration
backup_configuration() {
    log_step "Backing up configuration"
    
    local config_backup_dir="$BACKUP_DIR/config"
    
    # Backup all configuration files
    local config_files=(
        "$ROOT_DIR/.env*"
        "$CONFIG_DIR/*"
        "$ROOT_DIR/backend/*/config/*"
        "$ROOT_DIR/backend/*/settings/*"
        "$ROOT_DIR/infrastructure/*.yaml"
        "$ROOT_DIR/infrastructure/*.yml"
        "$ROOT_DIR/infrastructure/*.tf"
        "$ROOT_DIR/infrastructure/kubernetes/*.yaml"
        "$ROOT_DIR/docker-compose*.yml"
        "$ROOT_DIR/Makefile"
        "$ROOT_DIR/requirements*.txt"
        "$ROOT_DIR/pyproject.toml"
        "$ROOT_DIR/package.json"
    )
    
    for pattern in "${config_files[@]}"; do
        if ls $pattern >/dev/null 2>&1; then
            for file in $pattern; do
                if [ -f "$file" ]; then
                    local rel_path=$(realpath --relative-to="$ROOT_DIR" "$file")
                    local dest_dir="$config_backup_dir/$(dirname "$rel_path")"
                    
                    mkdir -p "$dest_dir"
                    cp -p "$file" "$dest_dir/"
                    
                    log_info "Backed up: $rel_path"
                fi
            done
        fi
    done
    
    # Create config manifest
    find "$config_backup_dir" -type f | sort > "$config_backup_dir/manifest.txt"
    
    cat > "$config_backup_dir/info.json" << EOF
{
  "component": "configuration",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$(date +%Y%m%d_%H%M%S)",
  "file_count": "$(find "$config_backup_dir" -type f | wc -l)",
  "total_size": "$(du -sh "$config_backup_dir" | cut -f1)",
  "includes": [".env files", "config directories", "docker-compose files", "infrastructure files"]
}
EOF
    
    log_success "Configuration backup completed"
    return 0
}

# Backup secrets
backup_secrets() {
    log_step "Backing up secrets"
    
    local secrets_backup_dir="$BACKUP_DIR/secrets"
    
    if [ ! -d "$SECRETS_DIR" ]; then
        log_warning "Secrets directory not found: $SECRETS_DIR"
        return 0
    fi
    
    log_info "Securely backing up secrets from: $SECRETS_DIR"
    
    # Create encrypted tar archive of secrets
    local secrets_tar="$TEMP_DIR/secrets.tar"
    
    tar -cf "$secrets_tar" -C "$SECRETS_DIR" . 2>> "$ERROR_LOG"
    
    if [ $? -eq 0 ]; then
        # Encrypt the tar file
        if [ "$ENCRYPTION" = "true" ] && [ -n "$ENCRYPTION_KEY" ]; then
            openssl enc -aes-256-cbc -salt -in "$secrets_tar" \
                -out "$secrets_backup_dir/secrets_encrypted.tar.enc" \
                -pass "pass:$ENCRYPTION_KEY" 2>> "$ERROR_LOG"
            
            if [ $? -eq 0 ]; then
                rm -f "$secrets_tar"
                log_success "Secrets backed up and encrypted"
            else
                log_error "Failed to encrypt secrets"
                return 1
            fi
        else
            mv "$secrets_tar" "$secrets_backup_dir/secrets.tar"
            log_warning "Secrets backed up without encryption"
        fi
        
        # Create security manifest
        cat > "$secrets_backup_dir/security_info.json" << EOF
{
  "component": "secrets",
  "source_directory": "$SECRETS_DIR",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$(date +%Y%m%d_%H%M%S)",
  "encryption": "$ENCRYPTION",
  "encryption_algorithm": "aes-256-cbc",
  "file_count": "$(find "$SECRETS_DIR" -type f | wc -l)",
  "backup_size": "$(du -h "$secrets_backup_dir" | cut -f1)",
  "permissions": "700",
  "warning": "This directory contains sensitive information. Handle with care."
}
EOF
        
        # Set secure permissions
        chmod 600 "$secrets_backup_dir"/*
        chmod 700 "$secrets_backup_dir"
    else
        log_error "Failed to create secrets archive"
        return 1
    fi
    
    return 0
}

# Backup logs
backup_logs() {
    log_step "Backing up logs"
    
    local logs_backup_dir="$BACKUP_DIR/logs"
    local logs_source="$ROOT_DIR/.logs"
    
    if [ ! -d "$logs_source" ]; then
        log_warning "Logs directory not found: $logs_source"
        return 0
    fi
    
    log_info "Backing up logs from: $logs_source"
    
    # Backup only recent logs (last 7 days)
    find "$logs_source" -name "*.log" -type f -mtime -7 -exec cp --parents {} "$logs_backup_dir/" \; 2>> "$ERROR_LOG"
    
    # Compress logs
    if [ "$COMPRESSION" != "none" ]; then
        log_info "Compressing logs..."
        
        find "$logs_backup_dir" -name "*.log" -type f | while read -r logfile; do
            case $COMPRESSION in
                "gzip")
                    gzip -f "$logfile"
                    ;;
                "bzip2")
                    bzip2 -f "$logfile"
                    ;;
                "xz")
                    xz -f "$logfile"
                    ;;
            esac
        done
    fi
    
    cat > "$logs_backup_dir/info.json" << EOF
{
  "component": "logs",
  "source_directory": "$logs_source",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$(date +%Y%m%d_%H%M%S)",
  "log_files": "$(find "$logs_backup_dir" -type f | wc -l)",
  "total_size": "$(du -sh "$logs_backup_dir" | cut -f1)",
  "compression": "$COMPRESSION",
  "retention_days": 7
}
EOF
    
    log_success "Logs backup completed"
    return 0
}

# Backup Docker volumes
backup_docker_volumes() {
    log_step "Backing up Docker volumes"
    
    local docker_backup_dir="$BACKUP_DIR/docker"
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not available, skipping Docker volumes backup"
        return 0
    fi
    
    # Get list of volumes
    local volumes=$(docker volume ls -q --filter "name=goat-prediction")
    
    if [ -z "$volumes" ]; then
        log_warning "No GOAT-PREDICTION Docker volumes found"
        return 0
    fi
    
    log_info "Found Docker volumes:"
    echo "$volumes" | while read -r volume; do
        log_info "  - $volume"
    done
    
    # Backup each volume
    for volume in $volumes; do
        log_info "Backing up volume: $volume"
        
        local backup_file="$docker_backup_dir/${volume}_$(date +%Y%m%d).tar"
        
        docker run --rm \
            -v "$volume:/source" \
            -v "$docker_backup_dir:/backup" \
            alpine tar -cf "/backup/$(basename "$backup_file")" -C /source . 2>> "$ERROR_LOG"
        
        if [ $? -eq 0 ]; then
            local size=$(du -h "$backup_file" | cut -f1)
            log_success "Volume $volume backed up: $size"
        else
            log_error "Failed to backup volume: $volume"
        fi
    done
    
    cat > "$docker_backup_dir/info.json" << EOF
{
  "component": "docker_volumes",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$(date +%Y%m%d_%H%M%S)",
  "volume_count": "$(echo "$volumes" | wc -l)",
  "volumes": [$(echo "$volumes" | sed 's/^/"/;s/$/"/' | tr '\n' ',')],
  "total_size": "$(du -sh "$docker_backup_dir" | cut -f1)"
}
EOF
    
    log_success "Docker volumes backup completed"
    return 0
}

# Backup Kubernetes resources
backup_kubernetes() {
    log_step "Backing up Kubernetes resources"
    
    local k8s_backup_dir="$BACKUP_DIR/kubernetes"
    
    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl not available, skipping Kubernetes backup"
        return 0
    fi
    
    # Get current context
    local context=$(kubectl config current-context 2>/dev/null || echo "unknown")
    
    log_info "Kubernetes context: $context"
    
    # Backup all resources in the namespace
    local namespace="goat-prediction-$ENVIRONMENT"
    local resources=(
        "deployments"
        "statefulsets"
        "daemonsets"
        "services"
        "configmaps"
        "secrets"
        "ingresses"
        "persistentvolumeclaims"
        "pods"
        "jobs"
        "cronjobs"
    )
    
    mkdir -p "$k8s_backup_dir/yaml"
    mkdir -p "$k8s_backup_dir/json"
    
    for resource in "${resources[@]}"; do
        log_info "Backing up resource: $resource"
        
        # Backup as YAML
        kubectl get "$resource" -n "$namespace" -o yaml > \
            "$k8s_backup_dir/yaml/${resource}_$(date +%Y%m%d).yaml" 2>> "$ERROR_LOG"
        
        # Backup as JSON
        kubectl get "$resource" -n "$namespace" -o json > \
            "$k8s_backup_dir/json/${resource}_$(date +%Y%m%d).json" 2>> "$ERROR_LOG"
    done
    
    # Backup custom resources
    if kubectl get crd 2>/dev/null | grep -q "predictions\|models"; then
        log_info "Backing up custom resources"
        
        kubectl get predictions -n "$namespace" -o yaml > \
            "$k8s_backup_dir/yaml/predictions_$(date +%Y%m%d).yaml" 2>> "$ERROR_LOG"
        
        kubectl get models -n "$namespace" -o yaml > \
            "$k8s_backup_dir/yaml/models_$(date +%Y%m%d).yaml" 2>> "$ERROR_LOG"
    fi
    
    # Backup cluster info
    kubectl cluster-info > "$k8s_backup_dir/cluster_info.txt" 2>> "$ERROR_LOG"
    kubectl get nodes -o wide > "$k8s_backup_dir/nodes.txt" 2>> "$ERROR_LOG"
    kubectl get all -n "$namespace" > "$k8s_backup_dir/all_resources.txt" 2>> "$ERROR_LOG"
    
    cat > "$k8s_backup_dir/info.json" << EOF
{
  "component": "kubernetes",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$(date +%Y%m%d_%H%M%S)",
  "context": "$context",
  "namespace": "$namespace",
  "resource_types": [$(printf '"%s",' "${resources[@]}" | sed 's/,$//')],
  "total_size": "$(du -sh "$k8s_backup_dir" | cut -f1)"
}
EOF
    
    log_success "Kubernetes backup completed"
    return 0
}

# Backup Terraform state
backup_terraform_state() {
    log_step "Backing up Terraform state"
    
    local tf_backup_dir="$BACKUP_DIR/terraform"
    local tf_dir="$ROOT_DIR/infrastructure/terraform"
    
    if [ ! -d "$tf_dir" ]; then
        log_warning "Terraform directory not found: $tf_dir"
        return 0
    fi
    
    log_info "Backing up Terraform state from: $tf_dir"
    
    # Copy all Terraform files
    cp -r "$tf_dir"/* "$tf_backup_dir/" 2>> "$ERROR_LOG"
    
    # Backup remote state if configured
    if [ -f "$tf_dir/terraform.tfstate" ] || [ -f "$tf_dir/terraform.tfstate.backup" ]; then
        log_info "Found local Terraform state, backing up..."
        
        # Create state backup
        if command -v terraform &> /dev/null; then
            cd "$tf_dir"
            terraform state pull > "$tf_backup_dir/terraform_state_$(date +%Y%m%d).json" 2>> "$ERROR_LOG"
        fi
    fi
    
    cat > "$tf_backup_dir/info.json" << EOF
{
  "component": "terraform",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$(date +%Y%m%d_%H%M%S)",
  "source_directory": "$tf_dir",
  "files": [$(find "$tf_backup_dir" -maxdepth 1 -type f -name "*.tf" -o -name "*.json" | xargs -I {} basename {} | sed 's/^/"/;s/$/"/' | tr '\n' ',')],
  "total_size": "$(du -sh "$tf_backup_dir" | cut -f1)"
}
EOF
    
    log_success "Terraform backup completed"
    return 0
}

# Create backup manifest
create_manifest() {
    log_step "Creating backup manifest"
    
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    local file_count=$(find "$BACKUP_DIR" -type f | wc -l)
    local dir_count=$(find "$BACKUP_DIR" -type d | wc -l)
    
    cat > "$MANIFEST_FILE" << EOF
{
  "backup": {
    "id": "$BACKUP_ID",
    "environment": "$ENVIRONMENT",
    "type": "$BACKUP_TYPE",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "created_by": "$(whoami)@$(hostname)",
    "total_size": "$total_size",
    "file_count": $file_count,
    "directory_count": $((dir_count - 1)),
    "compression": "$COMPRESSION",
    "encryption": "$ENCRYPTION"
  },
  "components": {
    "database": {
      "backed_up": "$([ -d "$BACKUP_DIR/database" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/database" ] && du -sh "$BACKUP_DIR/database" | cut -f1 || echo "0")"
    },
    "redis": {
      "backed_up": "$([ -d "$BACKUP_DIR/redis" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/redis" ] && du -sh "$BACKUP_DIR/redis" | cut -f1 || echo "0")"
    },
    "supabase": {
      "backed_up": "$([ -d "$BACKUP_DIR/supabase" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/supabase" ] && du -sh "$BACKUP_DIR/supabase" | cut -f1 || echo "0")"
    },
    "ml_models": {
      "backed_up": "$([ -d "$BACKUP_DIR/ml_models" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/ml_models" ] && du -sh "$BACKUP_DIR/ml_models" | cut -f1 || echo "0")"
    },
    "configuration": {
      "backed_up": "$([ -d "$BACKUP_DIR/config" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/config" ] && du -sh "$BACKUP_DIR/config" | cut -f1 || echo "0")"
    },
    "secrets": {
      "backed_up": "$([ -d "$BACKUP_DIR/secrets" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/secrets" ] && du -sh "$BACKUP_DIR/secrets" | cut -f1 || echo "0")"
    },
    "logs": {
      "backed_up": "$([ -d "$BACKUP_DIR/logs" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/logs" ] && du -sh "$BACKUP_DIR/logs" | cut -f1 || echo "0")"
    },
    "docker": {
      "backed_up": "$([ -d "$BACKUP_DIR/docker" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/docker" ] && du -sh "$BACKUP_DIR/docker" | cut -f1 || echo "0")"
    },
    "kubernetes": {
      "backed_up": "$([ -d "$BACKUP_DIR/kubernetes" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/kubernetes" ] && du -sh "$BACKUP_DIR/kubernetes" | cut -f1 || echo "0")"
    },
    "terraform": {
      "backed_up": "$([ -d "$BACKUP_DIR/terraform" ] && echo "true" || echo "false")",
      "size": "$([ -d "$BACKUP_DIR/terraform" ] && du -sh "$BACKUP_DIR/terraform" | cut -f1 || echo "0")"
    }
  },
  "verification": {
    "checksum_file": "$VERIFICATION_FILE",
    "verification_command": "md5sum -c $VERIFICATION_FILE"
  },
  "restore_instructions": "Use restore.sh script: ./scripts/maintenance/restore.sh --backup-id $BACKUP_ID"
}
EOF
    
    log_success "Manifest created: $MANIFEST_FILE"
}

# Create verification checksums
create_verification() {
    if [ "$VERIFY_BACKUP" != "true" ]; then
        log_info "Skipping backup verification"
        return 0
    fi
    
    log_step "Creating verification checksums"
    
    # Generate MD5 checksums for all files
    find "$BACKUP_DIR" -type f ! -name "*.md5" -exec md5sum {} \; > "$VERIFICATION_FILE" 2>> "$ERROR_LOG"
    
    if [ $? -eq 0 ]; then
        local checksum_count=$(wc -l < "$VERIFICATION_FILE")
        log_success "Verification checksums created: $checksum_count files"
        
        # Verify the checksums
        log_info "Verifying backup integrity..."
        if md5sum -c "$VERIFICATION_FILE" >> "$BACKUP_LOG" 2>> "$ERROR_LOG"; then
            log_success "Backup integrity verified successfully"
        else
            log_error "Backup integrity verification failed"
            return 1
        fi
    else
        log_error "Failed to create verification checksums"
        return 1
    fi
    
    return 0
}

# Compress backup
compress_backup() {
    if [ "$COMPRESSION" = "none" ]; then
        log_info "Compression disabled"
        return 0
    fi
    
    log_step "Compressing backup"
    
    local backup_name="goat_backup_${BACKUP_ID}"
    local compress_cmd=""
    local extension=""
    
    case $COMPRESSION in
        "gzip")
            compress_cmd="tar -czf"
            extension="tar.gz"
            ;;
        "bzip2")
            compress_cmd="tar -cjf"
            extension="tar.bz2"
            ;;
        "xz")
            compress_cmd="tar -cJf"
            extension="tar.xz"
            ;;
        *)
            log_error "Unsupported compression: $COMPRESSION"
            return 1
            ;;
    esac
    
    # Create compressed archive
    cd "$BACKUP_ROOT"
    $compress_cmd "${backup_name}.${extension}" "$BACKUP_ID" 2>> "$ERROR_LOG"
    
    if [ $? -eq 0 ]; then
        local compressed_size=$(du -h "${backup_name}.${extension}" | cut -f1)
        log_success "Backup compressed: ${backup_name}.${extension} ($compressed_size)"
        
        # Update manifest with compression info
        jq ".backup.compressed_size = \"$compressed_size\"" "$MANIFEST_FILE" > "$MANIFEST_FILE.tmp"
        mv "$MANIFEST_FILE.tmp" "$MANIFEST_FILE"
    else
        log_error "Backup compression failed"
        return 1
    fi
    
    return 0
}

# Upload to S3
upload_to_s3() {
    if [ "$UPLOAD_TO_S3" != "true" ]; then
        log_info "S3 upload disabled"
        return 0
    fi
    
    log_step "Uploading backup to S3"
    
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not available, cannot upload to S3"
        return 1
    fi
    
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        log_error "AWS credentials not set"
        return 1
    fi
    
    local backup_name="goat_backup_${BACKUP_ID}"
    local compressed_file="${backup_name}.tar.gz"
    
    if [ ! -f "$BACKUP_ROOT/$compressed_file" ]; then
        log_error "Compressed backup file not found: $compressed_file"
        return 1
    fi
    
    log_info "Uploading to S3: s3://$S3_BUCKET/$ENVIRONMENT/$compressed_file"
    
    # Upload to S3
    aws s3 cp "$BACKUP_ROOT/$compressed_file" \
        "s3://$S3_BUCKET/$ENVIRONMENT/$compressed_file" \
        --region "$S3_REGION" \
        --storage-class STANDARD_IA \
        --acl private 2>> "$ERROR_LOG"
    
    if [ $? -eq 0 ]; then
        log_success "Backup uploaded to S3 successfully"
        
        # Generate pre-signed URL (valid for 7 days)
        local presigned_url=$(aws s3 presign \
            "s3://$S3_BUCKET/$ENVIRONMENT/$compressed_file" \
            --expires-in 604800 \
            --region "$S3_REGION" 2>/dev/null)
        
        if [ -n "$presigned_url" ]; then
            echo "$presigned_url" > "$BACKUP_DIR/s3_presigned_url.txt"
            log_info "Pre-signed URL generated (valid 7 days)"
        fi
        
        # Update manifest with S3 info
        jq ".backup.s3_location = \"s3://$S3_BUCKET/$ENVIRONMENT/$compressed_file\"" "$MANIFEST_FILE" > "$MANIFEST_FILE.tmp"
        mv "$MANIFEST_FILE.tmp" "$MANIFEST_FILE"
    else
        log_error "Failed to upload backup to S3"
        return 1
    fi
    
    return 0
}

# Apply retention policy
apply_retention_policy() {
    log_step "Applying retention policy"
    
    local total_backups=$(find "$BACKUP_ROOT" -maxdepth 1 -type d -name "2*" | wc -l)
    local total_archives=$(find "$BACKUP_ROOT" -maxdepth 1 -type f -name "goat_backup_*.tar.*" | wc -l)
    
    log_info "Current backups: $total_backups directories, $total_archives archives"
    
    # Remove old backup directories (keep last 30 days)
    find "$BACKUP_ROOT" -maxdepth 1 -type d -name "2*" -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>> "$ERROR_LOG"
    
    # Remove old archive files (keep last 30 days)
    find "$BACKUP_ROOT" -maxdepth 1 -type f -name "goat_backup_*.tar.*" -mtime +$RETENTION_DAYS -delete 2>> "$ERROR_LOG"
    
    # Weekly backups - keep last 4 weeks
    if [ "$total_backups" -gt 4 ]; then
        find "$BACKUP_ROOT" -maxdepth 1 -type d -name "2*" | \
            sort -r | tail -n +5 | xargs rm -rf 2>> "$ERROR_LOG"
    fi
    
    # Monthly backups - keep last 12 months
    local monthly_backups=$(find "$BACKUP_ROOT" -maxdepth 1 -type f -name "goat_backup_*01_*.tar.*" | sort -r)
    local monthly_count=$(echo "$monthly_backups" | wc -l)
    
    if [ "$monthly_count" -gt "$RETENTION_MONTHS" ]; then
        echo "$monthly_backups" | tail -n +$((RETENTION_MONTHS + 1)) | xargs rm -f 2>> "$ERROR_LOG"
    fi
    
    # Cleanup empty directories
    find "$BACKUP_ROOT" -type d -empty -delete 2>> "$ERROR_LOG"
    
    log_success "Retention policy applied"
    
    # Report remaining backups
    local remaining_dirs=$(find "$BACKUP_ROOT" -maxdepth 1 -type d -name "2*" | wc -l)
    local remaining_archives=$(find "$BACKUP_ROOT" -maxdepth 1 -type f -name "goat_backup_*.tar.*" | wc -l)
    
    log_info "Remaining backups: $remaining_dirs directories, $remaining_archives archives"
}

# Cleanup temporary files
cleanup_temp_files() {
    log_step "Cleaning up temporary files"
    
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        log_success "Temporary files cleaned up"
    fi
    
    # Cleanup old log files (keep 30 days)
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>> "$ERROR_LOG"
    find "$LOG_DIR" -name "*.json" -mtime +30 -delete 2>> "$ERROR_LOG"
}

# Send notifications
send_notification() {
    local type=$1
    local message=$2
    
    if [ "$SEND_NOTIFICATIONS" != "true" ]; then
        return 0
    fi
    
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local subject="GOAT-PREDICTION Backup $type - $ENVIRONMENT"
    local full_message="Backup ID: $BACKUP_ID\nEnvironment: $ENVIRONMENT\nType: $BACKUP_TYPE\nTime: $timestamp\n\n$message"
    
    # Slack notification
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local slack_color=""
        case $type in
            "SUCCESS") slack_color="good" ;;
            "WARNING") slack_color="warning" ;;
            "ERROR") slack_color="danger" ;;
            *) slack_color="#439FE0" ;;
        esac
        
        local slack_payload=$(cat << EOF
{
  "attachments": [
    {
      "color": "$slack_color",
      "title": "🐐 GOAT-PREDICTION Backup $type",
      "fields": [
        {
          "title": "Backup ID",
          "value": "$BACKUP_ID",
          "short": true
        },
        {
          "title": "Environment",
          "value": "$ENVIRONMENT",
          "short": true
        },
        {
          "title": "Type",
          "value": "$BACKUP_TYPE",
          "short": true
        },
        {
          "title": "Status",
          "value": "$type",
          "short": true
        },
        {
          "title": "Message",
          "value": "$message",
          "short": false
        }
      ],
      "footer": "GOAT-PREDICTION Backup System",
      "ts": $(date +%s)
    }
  ]
}
EOF
        )
        
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$slack_payload" >> "$BACKUP_LOG" 2>> "$ERROR_LOG" || true
    fi
    
    # Email notification
    if [ -n "$EMAIL_RECIPIENTS" ]; then
        echo -e "$full_message" | \
            mail -s "$subject" "$EMAIL_RECIPIENTS" 2>> "$ERROR_LOG" || true
    fi
    
    log_info "Notification sent: $type"
}

# Generate backup report
generate_report() {
    log_step "Generating backup report"
    
    local report_file="$BACKUP_DIR/backup_report_${BACKUP_ID}.html"
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    local duration=$(( $(date +%s) - $START_TIME ))
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GOAT-PREDICTION Backup Report</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 30px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #2c3e50; margin-bottom: 10px; }
        .header .subtitle { color: #7f8c8d; font-size: 18px; }
        .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; margin: 10px 0; }
        .status-success { background: #2ecc71; color: white; }
        .status-error { background: #e74c3c; color: white; }
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }
        .info-card { background: #f8f9fa; border-left: 4px solid #3498db; padding: 20px; border-radius: 5px; }
        .info-card h3 { margin-top: 0; color: #2c3e50; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 30px 0; }
        .stat-card { background: white; border: 1px solid #e0e0e0; padding: 20px; text-align: center; border-radius: 8px; }
        .stat-card .number { font-size: 36px; font-weight: bold; color: #3498db; margin: 10px 0; }
        .components-table { width: 100%; border-collapse: collapse; margin: 30px 0; }
        .components-table th, .components-table td { padding: 15px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        .components-table th { background: #f8f9fa; font-weight: bold; color: #2c3e50; }
        .components-table tr:hover { background: #f5f5f5; }
        .timestamp { color: #7f8c8d; font-size: 14px; text-align: center; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐐 GOAT-PREDICTION Backup Report</h1>
            <div class="subtitle">Comprehensive backup report for ${ENVIRONMENT} environment</div>
            <div class="status-badge status-success">BACKUP SUCCESSFUL</div>
        </div>
        
        <div class="info-grid">
            <div class="info-card">
                <h3>Backup Information</h3>
                <p><strong>Backup ID:</strong> $BACKUP_ID</p>
                <p><strong>Environment:</strong> $ENVIRONMENT</p>
                <p><strong>Type:</strong> $BACKUP_TYPE</p>
                <p><strong>Timestamp:</strong> $(date '+%Y-%m-%d %H:%M:%S')</p>
            </div>
            
            <div class="info-card">
                <h3>System Information</h3>
                <p><strong>Hostname:</strong> $(hostname)</p>
                <p><strong>User:</strong> $(whoami)</p>
                <p><strong>Duration:</strong> ${duration} seconds</p>
                <p><strong>Total Size:</strong> $total_size</p>
            </div>
        </div>
        
        <h2>Backup Components</h2>
        <table class="components-table">
            <thead>
                <tr>
                    <th>Component</th>
                    <th>Status</th>
                    <th>Size</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
EOF
    
    # Add component rows
    for component in "${BACKUP_COMPONENTS[@]}"; do
        local component_dir="$BACKUP_DIR/${component}"
        local status="❌ Not backed up"
        local size="0"
        local details=""
        
        if [ -d "$component_dir" ]; then
            status="✅ Backed up"
            size=$(du -sh "$component_dir" | cut -f1)
            
            # Get specific details based on component
            case $component in
                "database")
                    details="PostgreSQL dump"
                    ;;
                "ml_models")
                    local model_count=$(find "$component_dir" -name "*.joblib" -o -name "*.pkl" -o -name "*.h5" -o -name "*.pt" | wc -l)
                    details="$model_count models"
                    ;;
                *)
                    details="$(find "$component_dir" -type f | wc -l) files"
                    ;;
            esac
        fi
        
        cat >> "$report_file" << EOF
                <tr>
                    <td>$(echo $component | tr '_' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')</td>
                    <td>$status</td>
                    <td>$size</td>
                    <td>$details</td>
                </tr>
EOF
    done
    
    cat >> "$report_file" << EOF
            </tbody>
        </table>
        
        <div class="timestamp">
            Report generated on $(date) by GOAT-PREDICTION Backup System v2.0.0
        </div>
    </div>
</body>
</html>
EOF
    
    log_success "Backup report generated: $report_file"
}

# Main backup function
backup() {
    log_step "Starting GOAT-PREDICTION Ultimate Backup"
    
    # Record start time
    local START_TIME=$(date +%s)
    
    # Update state
    update_backup_state "STARTED" "Backup process started"
    send_notification "STARTED" "Backup $BACKUP_ID started"
    
    # Execute backup steps
    local steps=(
        "check_prerequisites"
        "init_directories"
        "check_lock"
        "setup_encryption"
        "backup_database"
        "backup_redis"
        "backup_supabase"
        "backup_ml_models"
        "backup_configuration"
        "backup_secrets"
        "backup_logs"
        "backup_docker_volumes"
        "backup_kubernetes"
        "backup_terraform_state"
        "create_manifest"
        "create_verification"
        "compress_backup"
        "upload_to_s3"
        "apply_retention_policy"
        "cleanup_temp_files"
        "generate_report"
    )
    
    local failed_step=""
    local success_steps=0
    local total_steps=${#steps[@]}
    
    for step in "${steps[@]}"; do
        log_info "Executing step: $step"
        update_backup_state "RUNNING" "Executing $step" "$step"
        
        if $step; then
            log_success "Step completed: $step"
            success_steps=$((success_steps + 1))
        else
            log_error "Step failed: $step"
            failed_step="$step"
            break
        fi
    done
    
    # Calculate duration
    local END_TIME=$(date +%s)
    local DURATION=$((END_TIME - START_TIME))
    
    # Final state
    if [ -z "$failed_step" ]; then
        update_backup_state "SUCCESS" "Backup completed successfully in ${DURATION}s"
        send_notification "SUCCESS" "Backup $BACKUP_ID completed successfully in ${DURATION}s"
        log_success "🐐 Backup completed successfully in ${DURATION} seconds!"
        log_success "📦 Backup location: $BACKUP_DIR"
        log_success "📊 Success rate: $success_steps/$total_steps steps"
        return 0
    else
        update_backup_state "FAILED" "Backup failed at step: $failed_step"
        send_notification "ERROR" "Backup $BACKUP_ID failed at step: $failed_step"
        log_error "💥 Backup failed at step: $failed_step"
        log_error "📊 Success rate: $success_steps/$total_steps steps"
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
            -t|--type)
                BACKUP_TYPE="$2"
                shift 2
                ;;
            -c|--compression)
                COMPRESSION="$2"
                shift 2
                ;;
            --no-encryption)
                ENCRYPTION="false"
                shift
                ;;
            --encryption-key)
                ENCRYPTION_KEY_FILE="$2"
                shift 2
                ;;
            --upload-s3)
                UPLOAD_TO_S3="true"
                shift
                ;;
            --s3-bucket)
                S3_BUCKET="$2"
                shift 2
                ;;
            --no-verify)
                VERIFY_BACKUP="false"
                shift
                ;;
            --slack-webhook)
                SLACK_WEBHOOK_URL="$2"
                shift 2
                ;;
            --email)
                EMAIL_RECIPIENTS="$2"
                shift 2
                ;;
            --retention-days)
                RETENTION_DAYS="$2"
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
    mkdir -p "$(dirname "$BACKUP_LOG")"
    exec > >(tee -a "$BACKUP_LOG")
    exec 2> >(tee -a "$ERROR_LOG")
    
    # Show banner
    show_banner
    
    # Run backup
    if backup; then
        exit 0
    else
        exit 1
    fi
}

show_help() {
    cat << EOF
GOAT-PREDICTION Ultimate Backup Script

Usage: $0 [OPTIONS]

Options:
  -e, --environment ENV     Environment to backup (default: production)
  -t, --type TYPE          Backup type: full, incremental, differential (default: full)
  -c, --compression TYPE   Compression: gzip, bzip2, xz, none (default: gzip)
  --no-encryption          Disable encryption (not recommended)
  --encryption-key FILE    Path to encryption key file
  --upload-s3             Upload backup to AWS S3
  --s3-bucket BUCKET      S3 bucket name (default: goat-prediction-backups)
  --no-verify             Skip backup verification
  --slack-webhook URL     Slack webhook URL for notifications
  --email EMAILS          Email addresses for notifications (comma-separated)
  --retention-days DAYS   Number of days to keep backups (default: 30)
  --help                  Show this help message

Examples:
  $0 --environment production --type full --upload-s3
  $0 --environment staging --compression xz --slack-webhook https://hooks.slack.com/...
  $0 --environment development --no-encryption --no-verify

Environment Variables:
  DATABASE_URL           PostgreSQL connection string
  REDIS_URL              Redis connection string
  SUPABASE_URL           Supabase URL
  SUPABASE_KEY           Supabase API key
  AWS_ACCESS_KEY_ID      AWS access key for S3
  AWS_SECRET_ACCESS_KEY  AWS secret key for S3

Backup Components:
  - Database (PostgreSQL)
  - Redis
  - Supabase
  - ML Models
  - Configuration files
  - Secrets
  - Application logs
  - Docker volumes
  - Kubernetes resources
  - Terraform state

EOF
}

# =============================================================================
# EXECUTE
# =============================================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
