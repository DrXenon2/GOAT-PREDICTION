#!/bin/bash

# 🐐 GOAT-PREDICTION ULTIMATE - PERFORMANCE MONITORING SCRIPT
# Version: 2.0.0
# Description: Comprehensive performance monitoring and health checks for GOAT-PREDICTION platform
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
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Performance thresholds
CPU_WARNING=${CPU_WARNING:-80}
CPU_CRITICAL=${CPU_CRITICAL:-95}
MEMORY_WARNING=${MEMORY_WARNING:-80}
MEMORY_CRITICAL=${MEMORY_CRITICAL:-95}
DISK_WARNING=${DISK_WARNING:-80}
DISK_CRITICAL=${DISK_CRITICAL:-95}
LOAD_WARNING=${LOAD_WARNING:-$(nproc)}
LOAD_CRITICAL=${LOAD_CRITICAL:-$(($(nproc) * 2))}
LATENCY_WARNING=${LATENCY_WARNING:-100}  # ms
LATENCY_CRITICAL=${LATENCY_CRITICAL:-500}  # ms
ERROR_RATE_WARNING=${ERROR_RATE_WARNING:-1}  # %
ERROR_RATE_CRITICAL=${ERROR_RATE_CRITICAL:-5}  # %
THROUGHPUT_WARNING=${THROUGHPUT_WARNING:-1000}  # requests/sec
RESPONSE_TIME_WARNING=${RESPONSE_TIME_WARNING:-200}  # ms

# Monitoring configuration
ENVIRONMENT=${ENVIRONMENT:-"production"}
CHECK_INTERVAL=${CHECK_INTERVAL:-60}  # seconds
MONITORING_DURATION=${MONITORING_DURATION:-300}  # seconds
ALERT_ENABLED=${ALERT_ENABLED:-"true"}
METRICS_STORAGE=${METRICS_STORAGE:-"prometheus"}  # prometheus, influxdb, stdout
DASHBOARD_UPDATE=${DASHBOARD_UPDATE:-"true"}
PERFORMANCE_REPORT=${PERFORMANCE_REPORT:-"true"}
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
EMAIL_RECIPIENTS=${EMAIL_RECIPIENTS:-""}
PAGERDUTY_API_KEY=${PAGERDUTY_API_KEY:-""}

# Service endpoints
API_GATEWAY_URL=${API_GATEWAY_URL:-"http://localhost:8000"}
PREDICTION_ENGINE_URL=${PREDICTION_ENGINE_URL:-"http://localhost:8001"}
DATABASE_URL=${DATABASE_URL:-"postgresql://localhost:5432/goat_prediction"}
REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}
SUPABASE_URL=${SUPABASE_URL:-""}
PROMETHEUS_URL=${PROMETHEUS_URL:-"http://localhost:9090"}
GRAFANA_URL=${GRAFANA_URL:-"http://localhost:3000"}

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
MONITORING_DIR="$ROOT_DIR/.monitoring"
LOG_DIR="$ROOT_DIR/.logs/monitoring"
REPORT_DIR="$ROOT_DIR/.reports/performance"
CONFIG_DIR="$ROOT_DIR/.config"

# Files
MONITOR_LOG="$LOG_DIR/performance_$(date +%Y%m%d_%H%M%S).log"
ERROR_LOG="$LOG_DIR/errors_$(date +%Y%m%d_%H%M%S).log"
ALERT_LOG="$LOG_DIR/alerts_$(date +%Y%m%d_%H%M%S).log"
METRICS_FILE="$MONITORING_DIR/metrics_$(date +%Y%m%d_%H%M%S).json"
REPORT_FILE="$REPORT_DIR/performance_report_$(date +%Y%m%d_%H%M%S).html"
STATE_FILE="$MONITORING_DIR/state.json"
CONFIG_FILE="$CONFIG_DIR/monitoring.yaml"
LOCK_FILE="/tmp/goat_performance_monitor.lock"

# Performance metrics storage
declare -A METRICS
declare -A THRESHOLDS
declare -A ALERTS

# =============================================================================
# FUNCTIONS
# =============================================================================

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$MONITOR_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$MONITOR_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$MONITOR_LOG" "$ALERT_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$MONITOR_LOG" "$ERROR_LOG" "$ALERT_LOG"
}

log_metric() {
    echo -e "${PURPLE}[METRIC]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$MONITOR_LOG"
}

log_step() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${WHITE}STEP: $1${NC}"
    echo -e "${CYAN}========================================${NC}\n" | tee -a "$MONITOR_LOG"
}

# Banner display
show_banner() {
    clear
    cat << "EOF"

    ██████╗  ██████╗  █████╗ ████████╗    ██████╗ ███████╗██████╗ ███████╗ ██████╗ ██████╗ ███╗   ███╗ █████╗ ███╗   ██╗ ██████╗ 
    ██╔════╝ ██╔═══██╗██╔══██╗╚══██╔══╝    ██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗██╔══██╗████╗ ████║██╔══██╗████╗  ██║██╔════╝ 
    ██║  ███╗██║   ██║███████║   ██║       ██████╔╝█████╗  ██████╔╝█████╗  ██║   ██║██████╔╝██╔████╔██║███████║██╔██╗ ██║██║  ███╗
    ██║   ██║██║   ██║██╔══██║   ██║       ██╔═══╝ ██╔══╝  ██╔══██╗██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║██╔══██║██║╚██╗██║██║   ██║
    ╚██████╔╝╚██████╔╝██║  ██║   ██║       ██║     ███████╗██║  ██║██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║██║ ╚████║╚██████╔╝
    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝       ╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ 
    
    🐐 GOAT-PREDICTION ULTIMATE - PERFORMANCE MONITORING v2.0.0
    =============================================================================
    
EOF
    log_info "Starting performance monitoring"
    log_info "Environment: $ENVIRONMENT | Interval: ${CHECK_INTERVAL}s | Duration: ${MONITORING_DURATION}s"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites"
    
    local missing_tools=()
    
    # Check required tools
    declare -A tools=(
        ["curl"]="curl HTTP client"
        ["jq"]="jq JSON processor"
        ["bc"]="bc calculator"
        ["awk"]="awk text processor"
        ["sar"]="sysstat utilities"
        ["vmstat"]="vmstat system monitor"
        ["iostat"]="iostat disk monitor"
        ["netstat"]="netstat network monitor"
        ["ss"]="socket statistics"
        ["ping"]="ping network tool"
        ["ps"]="process status"
        ["top"]="top process monitor"
        ["free"]="free memory info"
        ["df"]="disk free"
        ["du"]="disk usage"
        ["uptime"]="system uptime"
        ["nproc"]="CPU count"
        ["lscpu"]="CPU info"
    )
    
    for cmd in "${!tools[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_tools+=("${tools[$cmd]} ($cmd)")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_warning "Missing monitoring tools:"
        for tool in "${missing_tools[@]}"; do
            log_warning "  - $tool"
        fi
        
        # Install sysstat if missing
        if [[ " ${missing_tools[@]} " =~ " sysstat utilities (sar) " ]]; then
            log_info "Attempting to install sysstat..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y sysstat
            elif command -v yum &> /dev/null; then
                sudo yum install -y sysstat
            fi
        fi
    fi
    
    # Create directories
    mkdir -p "$MONITORING_DIR" "$LOG_DIR" "$REPORT_DIR"
    
    log_success "Prerequisites check completed"
}

# Check lock file
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        local process_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
        
        if [ "$process_name" = "check-performance.sh" ] || [ "$process_name" = "bash" ]; then
            log_error "Performance monitoring is already running (PID: $pid)"
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

# Load configuration
load_configuration() {
    log_step "Loading monitoring configuration"
    
    # Load YAML config if exists
    if [ -f "$CONFIG_FILE" ]; then
        log_info "Loading configuration from: $CONFIG_FILE"
        
        # Parse YAML (simplified)
        if command -v yq &> /dev/null; then
            CPU_WARNING=$(yq e '.thresholds.cpu.warning // 80' "$CONFIG_FILE")
            CPU_CRITICAL=$(yq e '.thresholds.cpu.critical // 95' "$CONFIG_FILE")
            API_GATEWAY_URL=$(yq e '.endpoints.api_gateway // "http://localhost:8000"' "$CONFIG_FILE")
        fi
    fi
    
    # Set thresholds
    THRESHOLDS=(
        ["cpu_warning"]=$CPU_WARNING
        ["cpu_critical"]=$CPU_CRITICAL
        ["memory_warning"]=$MEMORY_WARNING
        ["memory_critical"]=$MEMORY_CRITICAL
        ["disk_warning"]=$DISK_WARNING
        ["disk_critical"]=$DISK_CRITICAL
        ["load_warning"]=$LOAD_WARNING
        ["load_critical"]=$LOAD_CRITICAL
        ["latency_warning"]=$LATENCY_WARNING
        ["latency_critical"]=$LATENCY_CRITICAL
        ["error_rate_warning"]=$ERROR_RATE_WARNING
        ["error_rate_critical"]=$ERROR_RATE_CRITICAL
    )
    
    log_success "Configuration loaded"
    log_info "CPU Thresholds: Warning=${CPU_WARNING}%, Critical=${CPU_CRITICAL}%"
    log_info "Memory Thresholds: Warning=${MEMORY_WARNING}%, Critical=${MEMORY_CRITICAL}%"
    log_info "API Gateway: $API_GATEWAY_URL"
}

# Initialize monitoring state
initialize_state() {
    log_step "Initializing monitoring state"
    
    cat > "$STATE_FILE" << EOF
{
  "monitoring": {
    "environment": "$ENVIRONMENT",
    "start_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "interval_seconds": $CHECK_INTERVAL,
    "duration_seconds": $MONITORING_DURATION,
    "status": "running"
  },
  "metrics": {
    "system": {},
    "services": {},
    "network": {},
    "database": {},
    "application": {}
  },
  "alerts": [],
  "checks_performed": 0,
  "checks_failed": 0
}
EOF
    
    log_success "Monitoring state initialized"
}

# Update monitoring state
update_state() {
    local key=$1
    local value=$2
    local type=${3:-"string"}
    
    if [ "$type" = "number" ]; then
        jq ".$key = $value" "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
    else
        jq ".$key = \"$value\"" "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
    fi
}

# Collect system metrics
collect_system_metrics() {
    log_step "Collecting system metrics"
    
    # CPU metrics
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    local cpu_cores=$(nproc)
    local load_avg=$(awk '{print $1","$2","$3}' /proc/loadavg)
    local load_1=$(echo $load_avg | cut -d',' -f1)
    
    # Memory metrics
    local memory_info=$(free -m | awk 'NR==2{printf "%.2f", $3*100/$2}')
    local swap_info=$(free -m | awk 'NR==3{printf "%.2f", $3*100/$2}')
    local total_memory=$(free -m | awk 'NR==2{print $2}')
    local used_memory=$(free -m | awk 'NR==2{print $3}')
    
    # Disk metrics
    local disk_usage=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')
    local disk_total=$(df -h / | awk 'NR==2{print $2}')
    local disk_used=$(df -h / | awk 'NR==2{print $3}')
    local disk_available=$(df -h / | awk 'NR==2{print $4}')
    
    # Network metrics
    local network_rx=$(cat /sys/class/net/$(ip route | awk '/default/ {print $5}')/statistics/rx_bytes)
    local network_tx=$(cat /sys/class/net/$(ip route | awk '/default/ {print $5}')/statistics/tx_bytes)
    
    # System info
    local uptime_seconds=$(awk '{print $1}' /proc/uptime)
    local processes=$(ps aux | wc -l)
    local users=$(who | wc -l)
    
    # Store metrics
    METRICS["system.cpu.usage"]=$cpu_usage
    METRICS["system.cpu.cores"]=$cpu_cores
    METRICS["system.load.1min"]=$load_1
    METRICS["system.load.5min"]=$(echo $load_avg | cut -d',' -f2)
    METRICS["system.load.15min"]=$(echo $load_avg | cut -d',' -f3)
    METRICS["system.memory.usage"]=$memory_info
    METRICS["system.memory.total_mb"]=$total_memory
    METRICS["system.memory.used_mb"]=$used_memory
    METRICS["system.swap.usage"]=$swap_info
    METRICS["system.disk.usage"]=$disk_usage
    METRICS["system.disk.total_gb"]=$disk_total
    METRICS["system.disk.used_gb"]=$disk_used
    METRICS["system.disk.available_gb"]=$disk_available
    METRICS["system.network.rx_bytes"]=$network_rx
    METRICS["system.network.tx_bytes"]=$network_tx
    METRICS["system.uptime.seconds"]=$uptime_seconds
    METRICS["system.processes.count"]=$processes
    METRICS["system.users.count"]=$users
    
    # Check thresholds
    check_threshold "CPU Usage" "$cpu_usage" "$CPU_WARNING" "$CPU_CRITICAL" "%"
    check_threshold "Memory Usage" "$memory_info" "$MEMORY_WARNING" "$MEMORY_CRITICAL" "%"
    check_threshold "Disk Usage" "$disk_usage" "$DISK_WARNING" "$DISK_CRITICAL" "%"
    check_threshold "Load Average" "$load_1" "$LOAD_WARNING" "$LOAD_CRITICAL" ""
    
    log_success "System metrics collected"
    log_metric "CPU: ${cpu_usage}% | Memory: ${memory_info}% | Disk: ${disk_usage}% | Load: ${load_1}"
}

# Collect service metrics
collect_service_metrics() {
    log_step "Collecting service metrics"
    
    # API Gateway health check
    check_service_health "api_gateway" "$API_GATEWAY_URL"
    
    # Prediction Engine health check
    check_service_health "prediction_engine" "$PREDICTION_ENGINE_URL"
    
    # Database health check
    check_database_health
    
    # Redis health check
    check_redis_health
    
    # Supabase health check (if configured)
    if [ -n "$SUPABASE_URL" ]; then
        check_supabase_health
    fi
    
    # Prometheus metrics (if available)
    check_prometheus_metrics
    
    log_success "Service metrics collected"
}

check_service_health() {
    local service_name=$1
    local service_url=$2
    
    log_info "Checking $service_name health: $service_url"
    
    local start_time=$(date +%s%N)
    
    # Try to get health endpoint
    local response=$(curl -s -f -m 10 "$service_url/health" 2>/dev/null || echo "{}")
    local status_code=$?
    
    local end_time=$(date +%s%N)
    local response_time=$(( (end_time - start_time) / 1000000 ))  # milliseconds
    
    if [ $status_code -eq 0 ]; then
        local status=$(echo "$response" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        
        if [ "$status" = "healthy" ] || [ "$status" = "up" ]; then
            METRICS["service.$service_name.healthy"]=1
            METRICS["service.$service_name.response_time_ms"]=$response_time
            log_success "$service_name is healthy (${response_time}ms)"
        else
            METRICS["service.$service_name.healthy"]=0
            log_warning "$service_name returned status: $status"
        fi
    else
        METRICS["service.$service_name.healthy"]=0
        METRICS["service.$service_name.response_time_ms"]=$response_time
        log_error "$service_name is unreachable (HTTP $status_code, ${response_time}ms)"
        ALERTS["$service_name"]="Service unreachable: $service_url"
    fi
    
    # Store response time for threshold checking
    if [ $response_time -gt $LATENCY_CRITICAL ]; then
        log_error "$service_name response time critical: ${response_time}ms > ${LATENCY_CRITICAL}ms"
        ALERTS["${service_name}_latency"]="High latency: ${response_time}ms"
    elif [ $response_time -gt $LATENCY_WARNING ]; then
        log_warning "$service_name response time warning: ${response_time}ms > ${LATENCY_WARNING}ms"
    fi
}

check_database_health() {
    log_info "Checking database health"
    
    if [ -z "$DATABASE_URL" ]; then
        log_warning "DATABASE_URL not set, skipping database check"
        return 0
    fi
    
    local start_time=$(date +%s%N)
    
    # Extract connection details
    local dbname=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/.*\/\([^?]*\).*/\1/p')
    local host=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:/]*\).*/\1/p')
    local port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\).*/\1/p')
    local user=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    local password=$(echo "$DATABASE_URL" | sed -n 's/.*:\([^@]*\)@.*/\1/p')
    
    # Check PostgreSQL connection
    export PGPASSWORD="$password"
    
    if psql -h "$host" -p "${port:-5432}" -U "$user" -d "$dbname" -c "SELECT 1;" -t 2>/dev/null; then
        local end_time=$(date +%s%N)
        local response_time=$(( (end_time - start_time) / 1000000 ))
        
        # Get database metrics
        local connections=$(psql -h "$host" -p "${port:-5432}" -U "$user" -d "$dbname" \
            -c "SELECT count(*) FROM pg_stat_activity WHERE datname = '$dbname';" -t 2>/dev/null | tr -d ' ')
        
        local max_connections=$(psql -h "$host" -p "${port:-5432}" -U "$user" -d "$dbname" \
            -c "SHOW max_connections;" -t 2>/dev/null | tr -d ' ')
        
        local connection_usage=$(echo "scale=2; $connections * 100 / $max_connections" | bc)
        
        # Get table sizes
        local db_size=$(psql -h "$host" -p "${port:-5432}" -U "$user" -d "$dbname" \
            -c "SELECT pg_size_pretty(pg_database_size('$dbname'));" -t 2>/dev/null | tr -d ' ')
        
        # Store metrics
        METRICS["database.postgres.healthy"]=1
        METRICS["database.postgres.response_time_ms"]=$response_time
        METRICS["database.postgres.connections"]=$connections
        METRICS["database.postgres.max_connections"]=$max_connections
        METRICS["database.postgres.connection_usage"]=$connection_usage
        METRICS["database.postgres.size"]=$db_size
        
        log_success "Database is healthy (${response_time}ms, ${connections}/${max_connections} connections, size: $db_size)"
        
        # Check connection usage threshold
        check_threshold "Database Connections" "$connection_usage" "80" "90" "%"
        
    else
        METRICS["database.postgres.healthy"]=0
        log_error "Database connection failed"
        ALERTS["database"]="Database connection failed: $DATABASE_URL"
    fi
    
    unset PGPASSWORD
}

check_redis_health() {
    log_info "Checking Redis health"
    
    if [ -z "$REDIS_URL" ]; then
        log_warning "REDIS_URL not set, skipping Redis check"
        return 0
    fi
    
    local start_time=$(date +%s%N)
    
    if redis-cli -u "$REDIS_URL" ping 2>/dev/null | grep -q "PONG"; then
        local end_time=$(date +%s%N)
        local response_time=$(( (end_time - start_time) / 1000000 ))
        
        # Get Redis metrics
        local redis_info=$(redis-cli -u "$REDIS_URL" info 2>/dev/null)
        
        local connected_clients=$(echo "$redis_info" | grep "connected_clients:" | cut -d: -f2)
        local used_memory=$(echo "$redis_info" | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
        local total_keys=$(echo "$redis_info" | grep "db0:keys=" | cut -d= -f2 | cut -d, -f1)
        local hit_rate=$(echo "$redis_info" | grep "keyspace_hits:" | cut -d: -f2)
        local miss_rate=$(echo "$redis_info" | grep "keyspace_misses:" | cut -d: -f2)
        
        local total_commands=$((hit_rate + miss_rate))
        local hit_percentage=0
        if [ $total_commands -gt 0 ]; then
            hit_percentage=$(echo "scale=2; $hit_rate * 100 / $total_commands" | bc)
        fi
        
        # Store metrics
        METRICS["database.redis.healthy"]=1
        METRICS["database.redis.response_time_ms"]=$response_time
        METRICS["database.redis.connected_clients"]=$connected_clients
        METRICS["database.redis.used_memory"]=$used_memory
        METRICS["database.redis.total_keys"]=${total_keys:-0}
        METRICS["database.redis.hit_rate"]=$hit_percentage
        
        log_success "Redis is healthy (${response_time}ms, ${connected_clients} clients, memory: $used_memory, hit rate: ${hit_percentage}%)"
        
        # Check Redis hit rate threshold
        if [ $(echo "$hit_percentage < 90" | bc) -eq 1 ]; then
            log_warning "Redis hit rate low: ${hit_percentage}%"
        fi
        
    else
        METRICS["database.redis.healthy"]=0
        log_error "Redis connection failed"
        ALERTS["redis"]="Redis connection failed: $REDIS_URL"
    fi
}

check_supabase_health() {
    log_info "Checking Supabase health"
    
    local start_time=$(date +%s%N)
    
    if curl -s -f -m 10 "$SUPABASE_URL/rest/v1/" -H "apikey: $SUPABASE_KEY" 2>/dev/null; then
        local end_time=$(date +%s%N)
        local response_time=$(( (end_time - start_time) / 1000000 ))
        
        METRICS["service.supabase.healthy"]=1
        METRICS["service.supabase.response_time_ms"]=$response_time
        
        log_success "Supabase is healthy (${response_time}ms)"
    else
        METRICS["service.supabase.healthy"]=0
        log_warning "Supabase connection failed"
    fi
}

check_prometheus_metrics() {
    log_info "Checking Prometheus metrics"
    
    if [ -z "$PROMETHEUS_URL" ]; then
        log_warning "PROMETHEUS_URL not set, skipping Prometheus check"
        return 0
    fi
    
    # Check if Prometheus is reachable
    if curl -s -f -m 5 "$PROMETHEUS_URL/-/healthy" 2>/dev/null; then
        METRICS["monitoring.prometheus.healthy"]=1
        
        # Query some key metrics from Prometheus
        local query_result=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=up" 2>/dev/null)
        local up_count=$(echo "$query_result" | jq '.data.result | length' 2>/dev/null || echo "0")
        
        METRICS["monitoring.prometheus.targets_up"]=$up_count
        log_success "Prometheus is healthy ($up_count targets up)"
        
    else
        METRICS["monitoring.prometheus.healthy"]=0
        log_warning "Prometheus is unreachable"
    fi
}

# Collect application metrics
collect_application_metrics() {
    log_step "Collecting application metrics"
    
    # API Gateway performance metrics
    check_api_performance
    
    # Prediction Engine performance metrics
    check_prediction_performance
    
    # Business metrics
    check_business_metrics
    
    log_success "Application metrics collected"
}

check_api_performance() {
    log_info "Checking API Gateway performance"
    
    local endpoints=(
        "/api/v1/predictions"
        "/api/v1/health"
        "/api/v1/metrics"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="$API_GATEWAY_URL$endpoint"
        local start_time=$(date +%s%N)
        
        # Make a simple GET request (or POST for predictions)
        local method="GET"
        local data=""
        
        if [ "$endpoint" = "/api/v1/predictions" ]; then
            method="POST"
            data='{"sport": "football", "match_id": "test"}'
        fi
        
        local response=$(curl -s -X "$method" -H "Content-Type: application/json" \
            -d "$data" -m 10 "$url" 2>/dev/null || echo "{}")
        local status_code=$?
        
        local end_time=$(date +%s%N)
        local response_time=$(( (end_time - start_time) / 1000000 ))
        
        local endpoint_name=$(echo "$endpoint" | tr '/' '_' | sed 's/^_//')
        
        if [ $status_code -eq 0 ]; then
            METRICS["api.$endpoint_name.response_time_ms"]=$response_time
            METRICS["api.$endpoint_name.available"]=1
            
            # Check response time threshold
            if [ $response_time -gt $RESPONSE_TIME_WARNING ]; then
                log_warning "API $endpoint response time high: ${response_time}ms"
                ALERTS["api_${endpoint_name}_slow"]="Slow response: ${response_time}ms"
            fi
        else
            METRICS["api.$endpoint_name.available"]=0
            METRICS["api.$endpoint_name.response_time_ms"]=$response_time
            log_error "API $endpoint failed (${response_time}ms)"
            ALERTS["api_${endpoint_name}_failed"]="Endpoint failed: $endpoint"
        fi
    done
}

check_prediction_performance() {
    log_info "Checking Prediction Engine performance"
    
    # Check prediction endpoint
    local url="$PREDICTION_ENGINE_URL/api/v1/predict"
    local start_time=$(date +%s%N)
    
    local prediction_data='{
        "sport": "football",
        "match_id": "test_perf_$(date +%s)",
        "home_team": "Test Home",
        "away_team": "Test Away",
        "features": {
            "home_form": 0.75,
            "away_form": 0.65,
            "h2h_advantage": 0.6
        }
    }'
    
    local response=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "$prediction_data" -m 15 "$url" 2>/dev/null || echo "{}")
    local status_code=$?
    
    local end_time=$(date +%s%N)
    local response_time=$(( (end_time - start_time) / 1000000 ))
    
    if [ $status_code -eq 0 ]; then
        local has_prediction=$(echo "$response" | jq '.prediction != null' 2>/dev/null || echo "false")
        
        if [ "$has_prediction" = "true" ]; then
            METRICS["prediction.response_time_ms"]=$response_time
            METRICS["prediction.success"]=1
            
            # Extract confidence if available
            local confidence=$(echo "$response" | jq '.prediction.confidence // 0' 2>/dev/null || echo "0")
            METRICS["prediction.confidence"]=$confidence
            
            log_success "Prediction successful (${response_time}ms, confidence: ${confidence})"
            
            # Check prediction latency
            if [ $response_time -gt 1000 ]; then
                log_warning "Prediction response time high: ${response_time}ms"
            fi
            
        else
            METRICS["prediction.success"]=0
            log_warning "Prediction returned without result"
        fi
    else
        METRICS["prediction.success"]=0
        log_error "Prediction request failed (${response_time}ms)"
        ALERTS["prediction_failed"]="Prediction engine failed: $url"
    fi
}

check_business_metrics() {
    log_info "Checking business metrics"
    
    # Try to get business metrics from API
    local metrics_url="$API_GATEWAY_URL/api/v1/analytics/metrics"
    
    if curl -s -f -m 10 "$metrics_url" 2>/dev/null; then
        # Parse business metrics if available
        local total_predictions=$(curl -s "$API_GATEWAY_URL/api/v1/analytics/stats" 2>/dev/null | \
            jq '.total_predictions // 0' 2>/dev/null || echo "0")
        
        local accuracy_rate=$(curl -s "$API_GATEWAY_URL/api/v1/analytics/stats" 2>/dev/null | \
            jq '.accuracy_rate // 0' 2>/dev/null || echo "0")
        
        local active_users=$(curl -s "$API_GATEWAY_URL/api/v1/analytics/users/active" 2>/dev/null | \
            jq '.count // 0' 2>/dev/null || echo "0")
        
        METRICS["business.total_predictions"]=$total_predictions
        METRICS["business.accuracy_rate"]=$accuracy_rate
        METRICS["business.active_users"]=$active_users
        
        log_info "Business metrics: $total_predictions predictions, ${accuracy_rate}% accuracy, $active_users active users"
        
        # Check accuracy threshold
        if [ $(echo "$accuracy_rate < 60" | bc) -eq 1 ]; then
            log_warning "Accuracy rate low: ${accuracy_rate}%"
            ALERTS["low_accuracy"]="Accuracy below 60%: ${accuracy_rate}%"
        fi
        
    else
        log_warning "Business metrics endpoint unavailable"
    fi
}

# Collect network metrics
collect_network_metrics() {
    log_step "Collecting network metrics"
    
    # Network connections
    local tcp_connections=$(ss -t state established | wc -l)
    local http_connections=$(ss -t state established sport = :8000 or sport = :8001 | wc -l)
    
    # Port checks
    local ports=("8000" "8001" "5432" "6379" "9090" "3000")
    
    for port in "${ports[@]}"; do
        if ss -tuln | grep -q ":$port "; then
            METRICS["network.port_$port.open"]=1
        else
            METRICS["network.port_$port.open"]=0
            log_warning "Port $port is not listening"
        fi
    done
    
    # Internet connectivity
    if ping -c 1 -W 2 8.8.8.8 2>/dev/null; then
        METRICS["network.internet_connected"]=1
    else
        METRICS["network.internet_connected"]=0
        log_warning "Internet connectivity check failed"
    fi
    
    # DNS resolution
    if nslookup google.com 2>/dev/null | grep -q "Address:"; then
        METRICS["network.dns_working"]=1
    else
        METRICS["network.dns_working"]=0
        log_warning "DNS resolution check failed"
    fi
    
    METRICS["network.tcp_connections"]=$tcp_connections
    METRICS["network.http_connections"]=$http_connections
    
    log_success "Network metrics collected"
    log_metric "TCP Connections: $tcp_connections | HTTP Connections: $http_connections"
}

# Check thresholds and generate alerts
check_threshold() {
    local metric_name=$1
    local value=$2
    local warning_threshold=$3
    local critical_threshold=$4
    local unit=$5
    
    # Skip if value is empty
    if [ -z "$value" ]; then
        return 0
    fi
    
    # Compare values (handle floating point)
    if (( $(echo "$value >= $critical_threshold" | bc -l) )); then
        log_error "CRITICAL: $metric_name is $value$unit (threshold: $critical_threshold$unit)"
        ALERTS["${metric_name// /_}"]="CRITICAL: $metric_name = $value$unit"
        return 2
    elif (( $(echo "$value >= $warning_threshold" | bc -l) )); then
        log_warning "WARNING: $metric_name is $value$unit (threshold: $warning_threshold$unit)"
        ALERTS["${metric_name// /_}"]="WARNING: $metric_name = $value$unit"
        return 1
    fi
    
    return 0
}

# Store metrics
store_metrics() {
    log_step "Storing metrics"
    
    local timestamp=$(date +%s)
    
    # Create metrics JSON
    local metrics_json="{"
    metrics_json+="\"timestamp\": $timestamp,"
    metrics_json+="\"environment\": \"$ENVIRONMENT\","
    metrics_json+="\"metrics\": {"
    
    local first=true
    for key in "${!METRICS[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            metrics_json+=","
        fi
        
        local value="${METRICS[$key]}"
        
        # Check if value is numeric
        if [[ "$value" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            metrics_json+="\"$key\": $value"
        else
            metrics_json+="\"$key\": \"$value\""
        fi
    done
    
    metrics_json+="},"
    metrics_json+="\"alerts\": ["
    
    first=true
    for alert_key in "${!ALERTS[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            metrics_json+=","
        fi
        metrics_json+="{\"key\": \"$alert_key\", \"message\": \"${ALERTS[$alert_key]}\"}"
    done
    
    metrics_json+="]"
    metrics_json+="}"
    
    # Write to file
    echo "$metrics_json" | jq '.' > "$METRICS_FILE"
    
    # Update state file
    local check_count=$(jq '.checks_performed' "$STATE_FILE")
    jq ".checks_performed = $((check_count + 1))" "$STATE_FILE" > "$STATE_FILE.tmp"
    mv "$STATE_FILE.tmp" "$STATE_FILE"
    
    # Send to Prometheus if configured
    if [ "$METRICS_STORAGE" = "prometheus" ] && [ -n "$PROMETHEUS_URL" ]; then
        send_to_prometheus
    fi
    
    log_success "Metrics stored: $METRICS_FILE"
}

send_to_prometheus() {
    log_info "Sending metrics to Prometheus"
    
    # Create Prometheus metrics format
    local prometheus_metrics=""
    
    for key in "${!METRICS[@]}"; do
        local value="${METRICS[$key]}"
        
        # Only send numeric metrics
        if [[ "$value" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            local metric_name="goat_prediction_$(echo "$key" | sed 's/\./_/g')"
            prometheus_metrics+="$metric_name $value\n"
        fi
    done
    
    # Push to Prometheus Pushgateway (if available)
    local pushgateway_url=$(echo "$PROMETHEUS_URL" | sed 's/9090/9091/')
    
    if curl -s -X POST "$pushgateway_url/metrics/job/goat_prediction/instance/$(hostname)" \
        --data-binary "$prometheus_metrics" 2>/dev/null; then
        log_success "Metrics pushed to Prometheus"
    else
        log_warning "Failed to push metrics to Prometheus"
    fi
}

# Generate performance report
generate_report() {
    if [ "$PERFORMANCE_REPORT" != "true" ]; then
        return 0
    fi
    
    log_step "Generating performance report"
    
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local duration=$(( $(date +%s) - $(jq -r '.monitoring.start_time' "$STATE_FILE" | date -f - +%s) ))
    local checks_performed=$(jq '.checks_performed' "$STATE_FILE")
    
    # Calculate averages
    local cpu_avg=$(echo "${METRICS[system.cpu.usage]}" | bc)
    local memory_avg=$(echo "${METRICS[system.memory.usage]}" | bc)
    local disk_avg=$(echo "${METRICS[system.disk.usage]}" | bc)
    
    # Determine overall status
    local overall_status="HEALTHY"
    local status_color="green"
    
    if [ ${#ALERTS[@]} -gt 0 ]; then
        overall_status="WARNING"
        status_color="orange"
        
        for alert in "${ALERTS[@]}"; do
            if [[ "$alert" == *"CRITICAL"* ]]; then
                overall_status="CRITICAL"
                status_color="red"
                break
            fi
        done
    fi
    
    cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GOAT-PREDICTION Performance Report</title>
    <style>
        :root {
            --healthy: #2ecc71;
            --warning: #f39c12;
            --critical: #e74c3c;
            --info: #3498db;
            --dark: #2c3e50;
            --light: #ecf0f1;
            --gray: #95a5a6;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: var(--dark);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
            background-size: 30px 30px;
            animation: float 20s linear infinite;
        }
        
        @keyframes float {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
        }
        
        .header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }
        
        .status-badge {
            display: inline-block;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1.5em;
            font-weight: bold;
            margin: 20px 0;
            background: var(--$status_color);
            color: white;
            position: relative;
            z-index: 1;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .dashboard {
            padding: 40px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
        }
        
        .metric-card {
            background: var(--light);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.2);
        }
        
        .metric-card.critical {
            border-left: 5px solid var(--critical);
            background: linear-gradient(to right, #ffeaea, white);
        }
        
        .metric-card.warning {
            border-left: 5px solid var(--warning);
            background: linear-gradient(to right, #fff3e6, white);
        }
        
        .metric-card.healthy {
            border-left: 5px solid var(--healthy);
            background: linear-gradient(to right, #e8f7ef, white);
        }
        
        .metric-title {
            font-size: 1.2em;
            font-weight: bold;
            color: var(--dark);
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .metric-unit {
            font-size: 1em;
            color: var(--gray);
            margin-left: 5px;
        }
        
        .progress-bar {
            height: 10px;
            background: #ddd;
            border-radius: 5px;
            margin: 15px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            border-radius: 5px;
            transition: width 1s ease-in-out;
        }
        
        .thresholds {
            display: flex;
            justify-content: space-between;
            font-size: 0.9em;
            color: var(--gray);
            margin-top: 10px;
        }
        
        .alerts-section {
            grid-column: 1 / -1;
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .alerts-title {
            font-size: 1.5em;
            font-weight: bold;
            color: var(--dark);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .alert-item {
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .alert-critical {
            background: linear-gradient(to right, #ffeaea, #fff0f0);
            border-left: 5px solid var(--critical);
        }
        
        .alert-warning {
            background: linear-gradient(to right, #fff3e6, #fff8f0);
            border-left: 5px solid var(--warning);
        }
        
        .alert-info {
            background: linear-gradient(to right, #e6f2ff, #f0f8ff);
            border-left: 5px solid var(--info);
        }
        
        .alert-icon {
            font-size: 1.5em;
        }
        
        .footer {
            background: var(--dark);
            color: white;
            padding: 30px;
            text-align: center;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 30px 0;
        }
        
        .summary-item {
            text-align: center;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }
        
        .summary-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .summary-label {
            font-size: 0.9em;
            opacity: 0.8;
        }
        
        .service-status {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .service-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: var(--light);
            border-radius: 10px;
        }
        
        .service-name {
            font-weight: bold;
        }
        
        .service-status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .status-up {
            background: var(--healthy);
            color: white;
        }
        
        .status-down {
            background: var(--critical);
            color: white;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2em;
            }
            
            .dashboard {
                padding: 20px;
                grid-template-columns: 1fr;
            }
            
            .summary-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
    <script>
        function updateProgressBars() {
            document.querySelectorAll('.progress-fill').forEach(bar => {
                const value = bar.getAttribute('data-value');
                bar.style.width = Math.min(value, 100) + '%';
                bar.style.background = value > 90 ? '#e74c3c' : value > 80 ? '#f39c12' : '#2ecc71';
            });
        }
        
        function refreshMetrics() {
            fetch('/api/v1/metrics/latest')
                .then(response => response.json())
                .then(data => {
                    // Update metric values
                    document.getElementById('cpu-value').textContent = data.cpu_usage.toFixed(1);
                    document.getElementById('cpu-bar').setAttribute('data-value', data.cpu_usage);
                    
                    document.getElementById('memory-value').textContent = data.memory_usage.toFixed(1);
                    document.getElementById('memory-bar').setAttribute('data-value', data.memory_usage);
                    
                    // Update progress bars
                    updateProgressBars();
                })
                .catch(error => console.error('Error refreshing metrics:', error));
        }
        
        // Initialize progress bars
        document.addEventListener('DOMContentLoaded', function() {
            updateProgressBars();
            // Auto-refresh every 30 seconds
            setInterval(refreshMetrics, 30000);
        });
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐐 GOAT-PREDICTION Performance Report</h1>
            <div class="subtitle">Comprehensive performance monitoring dashboard</div>
            <div class="status-badge">$overall_status</div>
        </div>
        
        <div class="dashboard">
            <!-- System Metrics -->
            <div class="metric-card $(get_status_class "$cpu_avg" "$CPU_WARNING" "$CPU_CRITICAL")">
                <div class="metric-title">
                    <span>⚡</span> CPU Usage
                </div>
                <div class="metric-value">
                    <span id="cpu-value">$(printf "%.1f" "$cpu_avg")</span>
                    <span class="metric-unit">%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="cpu-bar" data-value="$cpu_avg"></div>
                </div>
                <div class="thresholds">
                    <span>Normal: &lt;${CPU_WARNING}%</span>
                    <span>Warning: ${CPU_WARNING}%</span>
                    <span>Critical: ${CPU_CRITICAL}%</span>
                </div>
            </div>
            
            <div class="metric-card $(get_status_class "$memory_avg" "$MEMORY_WARNING" "$MEMORY_CRITICAL")">
                <div class="metric-title">
                    <span>💾</span> Memory Usage
                </div>
                <div class="metric-value">
                    <span id="memory-value">$(printf "%.1f" "$memory_avg")</span>
                    <span class="metric-unit">%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="memory-bar" data-value="$memory_avg"></div>
                </div>
                <div class="thresholds">
                    <span>Normal: &lt;${MEMORY_WARNING}%</span>
                    <span>Warning: ${MEMORY_WARNING}%</span>
                    <span>Critical: ${MEMORY_CRITICAL}%</span>
                </div>
            </div>
            
            <div class="metric-card $(get_status_class "$disk_avg" "$DISK_WARNING" "$DISK_CRITICAL")">
                <div class="metric-title">
                    <span>💿</span> Disk Usage
                </div>
                <div class="metric-value">
                    <span>$(printf "%.1f" "$disk_avg")</span>
                    <span class="metric-unit">%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" data-value="$disk_avg"></div>
                </div>
                <div class="thresholds">
                    <span>Normal: &lt;${DISK_WARNING}%</span>
                    <span>Warning: ${DISK_WARNING}%</span>
                    <span>Critical: ${DISK_CRITICAL}%</span>
                </div>
            </div>
            
            <!-- Service Status -->
            <div class="metric-card">
                <div class="metric-title">
                    <span>🔗</span> Service Status
                </div>
                <div class="service-status">
                    <div class="service-item">
                        <span class="service-name">API Gateway</span>
                        <span class="service-status-badge $(get_service_status_class "${METRICS[service.api_gateway.healthy]}")">
                            $(get_service_status_text "${METRICS[service.api_gateway.healthy]}")
                        </span>
                    </div>
                    <div class="service-item">
                        <span class="service-name">Prediction Engine</span>
                        <span class="service-status-badge $(get_service_status_class "${METRICS[service.prediction_engine.healthy]}")">
                            $(get_service_status_text "${METRICS[service.prediction_engine.healthy]}")
                        </span>
                    </div>
                    <div class="service-item">
                        <span class="service-name">Database</span>
                        <span class="service-status-badge $(get_service_status_class "${METRICS[database.postgres.healthy]}")">
                            $(get_service_status_text "${METRICS[database.postgres.healthy]}")
                        </span>
                    </div>
                    <div class="service-item">
                        <span class="service-name">Redis</span>
                        <span class="service-status-badge $(get_service_status_class "${METRICS[database.redis.healthy]}")">
                            $(get_service_status_text "${METRICS[database.redis.healthy]}")
                        </span>
                    </div>
                </div>
            </div>
            
            <!-- Summary Stats -->
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value">$checks_performed</div>
                    <div class="summary-label">Checks Performed</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${#ALERTS[@]}</div>
                    <div class="summary-label">Active Alerts</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${duration}s</div>
                    <div class="summary-label">Monitoring Duration</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">$ENVIRONMENT</div>
                    <div class="summary-label">Environment</div>
                </div>
            </div>
            
            <!-- Alerts Section -->
            <div class="alerts-section">
                <div class="alerts-title">
                    <span>🚨</span> Active Alerts
                </div>
EOF
    
    if [ ${#ALERTS[@]} -eq 0 ]; then
        cat >> "$REPORT_FILE" << EOF
                <div class="alert-item alert-info">
                    <span class="alert-icon">✅</span>
                    <span>No active alerts. All systems are operating normally.</span>
                </div>
EOF
    else
        for alert in "${ALERTS[@]}"; do
            local alert_class="alert-warning"
            if [[ "$alert" == *"CRITICAL"* ]]; then
                alert_class="alert-critical"
            fi
            
            cat >> "$REPORT_FILE" << EOF
                <div class="alert-item $alert_class">
                    <span class="alert-icon">$(if [[ "$alert" == *"CRITICAL"* ]]; then echo "🔥"; else echo "⚠️"; fi)</span>
                    <span>$alert</span>
                </div>
EOF
        done
    fi
    
    cat >> "$REPORT_FILE" << EOF
            </div>
        </div>
        
        <div class="footer">
            <p>Report generated on $timestamp by GOAT-PREDICTION Performance Monitor v2.0.0</p>
            <p>Next update in ${CHECK_INTERVAL} seconds | <a href="$REPORT_FILE" style="color: #3498db;">Download Full Report</a></p>
        </div>
    </div>
</body>
</html>
EOF
    
    log_success "Performance report generated: $REPORT_FILE"
    
    # Also generate a simple text summary
    generate_text_summary
}

get_status_class() {
    local value=$1
    local warning=$2
    local critical=$3
    
    if (( $(echo "$value >= $critical" | bc -l) )); then
        echo "critical"
    elif (( $(echo "$value >= $warning" | bc -l) )); then
        echo "warning"
    else
        echo "healthy"
    fi
}

get_service_status_class() {
    local status=$1
    
    if [ "$status" = "1" ]; then
        echo "status-up"
    else
        echo "status-down"
    fi
}

get_service_status_text() {
    local status=$1
    
    if [ "$status" = "1" ]; then
        echo "UP"
    else
        echo "DOWN"
    fi
}

generate_text_summary() {
    local summary_file="$REPORT_DIR/summary_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$summary_file" << EOF
================================================================================
GOAT-PREDICTION PERFORMANCE SUMMARY
================================================================================
Generated: $(date)
Environment: $ENVIRONMENT
Duration: ${MONITORING_DURATION}s
Checks Performed: $(jq '.checks_performed' "$STATE_FILE")
Overall Status: $(if [ ${#ALERTS[@]} -eq 0 ]; then echo "HEALTHY"; else echo "ISSUES DETECTED"; fi)

SYSTEM METRICS:
  CPU Usage: ${METRICS[system.cpu.usage]}% (Warning: ${CPU_WARNING}%, Critical: ${CPU_CRITICAL}%)
  Memory Usage: ${METRICS[system.memory.usage]}% (Warning: ${MEMORY_WARNING}%, Critical: ${MEMORY_CRITICAL}%)
  Disk Usage: ${METRICS[system.disk.usage]}% (Warning: ${DISK_WARNING}%, Critical: ${DISK_CRITICAL}%)
  Load Average: ${METRICS[system.load.1min]} (Cores: ${METRICS[system.cpu.cores]})
  Uptime: $(awk '{printf "%dd %dh %dm", int($1/86400), int(($1%86400)/3600), int(($1%3600)/60)}' <<< "${METRICS[system.uptime.seconds]}")

SERVICE STATUS:
  API Gateway: $(if [ "${METRICS[service.api_gateway.healthy]}" = "1" ]; then echo "HEALTHY (${METRICS[service.api_gateway.response_time_ms]}ms)"; else echo "UNHEALTHY"; fi)
  Prediction Engine: $(if [ "${METRICS[service.prediction_engine.healthy]}" = "1" ]; then echo "HEALTHY (${METRICS[service.prediction_engine.response_time_ms]}ms)"; else echo "UNHEALTHY"; fi)
  Database: $(if [ "${METRICS[database.postgres.healthy]}" = "1" ]; then echo "HEALTHY (${METRICS[database.postgres.response_time_ms]}ms)"; else echo "UNHEALTHY"; fi)
  Redis: $(if [ "${METRICS[database.redis.healthy]}" = "1" ]; then echo "HEALTHY (${METRICS[database.redis.response_time_ms]}ms)"; else echo "UNHEALTHY"; fi)

BUSINESS METRICS:
  Total Predictions: ${METRICS[business.total_predictions]:-0}
  Accuracy Rate: ${METRICS[business.accuracy_rate]:-0}%
  Active Users: ${METRICS[business.active_users]:-0}

NETWORK METRICS:
  TCP Connections: ${METRICS[network.tcp_connections]:-0}
  HTTP Connections: ${METRICS[network.http_connections]:-0}
  Internet: $(if [ "${METRICS[network.internet_connected]}" = "1" ]; then echo "CONNECTED"; else echo "DISCONNECTED"; fi)
  DNS: $(if [ "${METRICS[network.dns_working]}" = "1" ]; then echo "WORKING"; else echo "FAILING"; fi)

ACTIVE ALERTS: ${#ALERTS[@]}
$(if [ ${#ALERTS[@]} -gt 0 ]; then
    for alert in "${ALERTS[@]}"; do
        echo "  - $alert"
    done
else
    echo "  None"
fi)

RECOMMENDATIONS:
$(generate_recommendations)

FILES:
  Full Report: $REPORT_FILE
  Metrics Data: $METRICS_FILE
  Monitor Log: $MONITOR_LOG
  Alert Log: $ALERT_LOG

================================================================================
EOF
    
    log_success "Text summary generated: $summary_file"
}

generate_recommendations() {
    local recommendations=""
    
    # CPU recommendations
    if (( $(echo "${METRICS[system.cpu.usage]} >= $CPU_CRITICAL" | bc -l) )); then
        recommendations+="  • CPU usage critical. Consider:\n"
        recommendations+="    - Scaling up compute resources\n"
        recommendations+="    - Optimizing application code\n"
        recommendations+="    - Implementing rate limiting\n"
    elif (( $(echo "${METRICS[system.cpu.usage]} >= $CPU_WARNING" | bc -l) )); then
        recommendations+="  • CPU usage high. Monitor closely.\n"
    fi
    
    # Memory recommendations
    if (( $(echo "${METRICS[system.memory.usage]} >= $MEMORY_CRITICAL" | bc -l) )); then
        recommendations+="  • Memory usage critical. Consider:\n"
        recommendations+="    - Adding more RAM\n"
        recommendations+="    - Optimizing memory usage\n"
        recommendations+="    - Restarting memory-intensive services\n"
    fi
    
    # Database recommendations
    if [ "${METRICS[database.postgres.connection_usage]}" ] && \
       (( $(echo "${METRICS[database.postgres.connection_usage]} >= 80" | bc -l) )); then
        recommendations+="  • Database connection usage high. Consider increasing max_connections.\n"
    fi
    
    # Redis recommendations
    if [ "${METRICS[database.redis.hit_rate]}" ] && \
       (( $(echo "${METRICS[database.redis.hit_rate]} < 90" | bc -l) )); then
        recommendations+="  • Redis hit rate low (${METRICS[database.redis.hit_rate]}%). Consider:\n"
        recommendations+="    - Increasing Redis memory\n"
        recommendations+="    - Reviewing cache strategies\n"
    fi
    
    # Service recommendations
    if [ "${METRICS[service.api_gateway.response_time_ms]}" ] && \
       (( ${METRICS[service.api_gateway.response_time_ms]} > $LATENCY_WARNING )); then
        recommendations+="  • API Gateway response time high. Consider:\n"
        recommendations+="    - Adding caching layer\n"
        recommendations+="    - Load balancing\n"
        recommendations+="    - Database query optimization\n"
    fi
    
    if [ -z "$recommendations" ]; then
        recommendations="  • All systems operating within normal parameters. Continue monitoring.\n"
    fi
    
    echo -e "$recommendations"
}

# Send alerts
send_alerts() {
    if [ "$ALERT_ENABLED" != "true" ] || [ ${#ALERTS[@]} -eq 0 ]; then
        return 0
    fi
    
    log_step "Sending alerts"
    
    local alert_count=${#ALERTS[@]}
    local alert_summary="GOAT-PREDICTION Performance Alerts ($alert_count issues)"
    local alert_details="Environment: $ENVIRONMENT\nTimestamp: $(date)\n\n"
    
    for alert in "${ALERTS[@]}"; do
        alert_details+="• $alert\n"
    done
    
    alert_details+="\nView full report: $REPORT_FILE"
    
    # Slack alert
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        send_slack_alert "$alert_summary" "$alert_details"
    fi
    
    # Email alert
    if [ -n "$EMAIL_RECIPIENTS" ]; then
        send_email_alert "$alert_summary" "$alert_details"
    fi
    
    # PagerDuty alert (for critical issues)
    if [ -n "$PAGERDUTY_API_KEY" ] && [[ "${ALERTS[@]}" =~ "CRITICAL" ]]; then
        send_pagerduty_alert "$alert_summary" "$alert_details"
    fi
    
    log_success "Alerts sent"
}

send_slack_alert() {
    local summary=$1
    local details=$2
    
    local color="warning"
    if [[ "$details" =~ "CRITICAL" ]]; then
        color="danger"
    fi
    
    local slack_payload=$(cat << EOF
{
  "attachments": [
    {
      "color": "$color",
      "title": "🚨 $summary",
      "text": "$details",
      "fields": [
        {
          "title": "Environment",
          "value": "$ENVIRONMENT",
          "short": true
        },
        {
          "title": "Time",
          "value": "$(date)",
          "short": true
        }
      ],
      "footer": "GOAT-PREDICTION Performance Monitor",
      "ts": $(date +%s)
    }
  ]
}
EOF
    )
    
    curl -s -X POST "$SLACK_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "$slack_payload" >> "$MONITOR_LOG" 2>> "$ERROR_LOG" || log_warning "Failed to send Slack alert"
}

send_email_alert() {
    local subject=$1
    local body=$2
    
    echo -e "$body" | mail -s "$subject" "$EMAIL_RECIPIENTS" 2>> "$ERROR_LOG" || \
        log_warning "Failed to send email alert"
}

send_pagerduty_alert() {
    local summary=$1
    local details=$2
    
    local pagerduty_payload=$(cat << EOF
{
  "routing_key": "$PAGERDUTY_API_KEY",
  "event_action": "trigger",
  "dedup_key": "goat-performance-$(date +%s)",
  "payload": {
    "summary": "$summary",
    "source": "goat-prediction-monitor",
    "severity": "critical",
    "component": "performance-monitoring",
    "group": "platform",
    "class": "performance_issue",
    "custom_details": {
      "environment": "$ENVIRONMENT",
      "alert_count": ${#ALERTS[@]},
      "details": "$details"
    }
  }
}
EOF
    )
    
    curl -s -X POST "https://events.pagerduty.com/v2/enqueue" \
        -H "Content-Type: application/json" \
        -d "$pagerduty_payload" >> "$MONITOR_LOG" 2>> "$ERROR_LOG" || \
        log_warning "Failed to send PagerDuty alert"
}

# Update dashboard
update_dashboard() {
    if [ "$DASHBOARD_UPDATE" != "true" ]; then
        return 0
    fi
    
    log_step "Updating monitoring dashboard"
    
    # Copy report to web-accessible location
    local web_dir="/var/www/html/monitoring"
    
    if [ -d "$web_dir" ]; then
        cp "$REPORT_FILE" "$web_dir/latest.html"
        cp "$REPORT_FILE" "$web_dir/archive/report_$(date +%Y%m%d_%H%M%S).html"
        log_success "Dashboard updated at $web_dir/latest.html"
    else
        log_info "Web directory not found, skipping dashboard update"
    fi
}

# Main monitoring loop
monitor() {
    log_step "Starting performance monitoring"
    
    local start_time=$(date +%s)
    local end_time=$((start_time + MONITORING_DURATION))
    local iteration=0
    
    # Initial state
    initialize_state
    
    while [ $(date +%s) -lt $end_time ]; do
        iteration=$((iteration + 1))
        local current_time=$(date '+%Y-%m-%d %H:%M:%S')
        
        log_info "=== Monitoring Iteration $iteration ($current_time) ==="
        
        # Clear previous metrics and alerts
        METRICS=()
        ALERTS=()
        
        # Collect all metrics
        collect_system_metrics
        collect_service_metrics
        collect_application_metrics
        collect_network_metrics
        
        # Store and process metrics
        store_metrics
        
        # Generate report every 5 iterations or on last iteration
        if [ $((iteration % 5)) -eq 0 ] || [ $(date +%s) -ge $((end_time - CHECK_INTERVAL)) ]; then
            generate_report
            send_alerts
            update_dashboard
        fi
        
        # Update state
        update_state "monitoring.status" "running"
        update_state "metrics.last_update" "$current_time"
        
        # Wait for next interval (unless it's the last iteration)
        if [ $(date +%s) -lt $((end_time - CHECK_INTERVAL)) ]; then
            log_info "Waiting ${CHECK_INTERVAL} seconds for next check..."
            sleep "$CHECK_INTERVAL"
        fi
    done
    
    # Final report
    generate_report
    send_alerts
    update_dashboard
    
    # Update final state
    update_state "monitoring.status" "completed"
    update_state "monitoring.end_time" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    
    local total_duration=$(( $(date +%s) - start_time ))
    log_success "🎉 Performance monitoring completed in ${total_duration} seconds"
    log_success "📊 Report generated: $REPORT_FILE"
    log_success "📈 Metrics stored: $METRICS_FILE"
    
    if [ ${#ALERTS[@]} -gt 0 ]; then
        log_warning "⚠️  ${#ALERTS[@]} alerts detected. Check $ALERT_LOG for details."
    else
        log_success "✅ All systems operating within normal parameters."
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
            -i|--interval)
                CHECK_INTERVAL="$2"
                shift 2
                ;;
            -d|--duration)
                MONITORING_DURATION="$2"
                shift 2
                ;;
            --cpu-warning)
                CPU_WARNING="$2"
                shift 2
                ;;
            --cpu-critical)
                CPU_CRITICAL="$2"
                shift 2
                ;;
            --no-alerts)
                ALERT_ENABLED="false"
                shift
                ;;
            --no-report)
                PERFORMANCE_REPORT="false"
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
    mkdir -p "$(dirname "$MONITOR_LOG")"
    exec > >(tee -a "$MONITOR_LOG")
    exec 2> >(tee -a "$ERROR_LOG")
    
    # Show banner
    show_banner
    
    # Check prerequisites and lock
    check_prerequisites
    check_lock
    
    # Load configuration
    load_configuration
    
    # Run monitoring
    if monitor; then
        exit 0
    else
        exit 1
    fi
}

show_help() {
    cat << EOF
GOAT-PREDICTION Ultimate Performance Monitoring Script

Usage: $0 [OPTIONS]

Options:
  -e, --environment ENV    Environment to monitor (default: production)
  -i, --interval SECONDS   Check interval in seconds (default: 60)
  -d, --duration SECONDS   Total monitoring duration (default: 300)
  --cpu-warning PERCENT    CPU warning threshold (default: 80)
  --cpu-critical PERCENT   CPU critical threshold (default: 95)
  --no-alerts              Disable alert notifications
  --no-report              Disable report generation
  --slack-webhook URL      Slack webhook URL for alerts
  --email EMAILS           Email addresses for alerts (comma-separated)
  --help                   Show this help message

Examples:
  $0 --environment production --interval 30 --duration 600
  $0 --environment staging --cpu-warning 70 --cpu-critical 90
  $0 --environment production --slack-webhook https://hooks.slack.com/...

Environment Variables:
  API_GATEWAY_URL          API Gateway endpoint (default: http://localhost:8000)
  PREDICTION_ENGINE_URL    Prediction Engine endpoint (default: http://localhost:8001)
  DATABASE_URL             PostgreSQL connection string
  REDIS_URL                Redis connection string
  SUPABASE_URL             Supabase URL
  SUPABASE_KEY             Supabase API key
  PROMETHEUS_URL           Prometheus endpoint (default: http://localhost:9090)
  GRAFANA_URL              Grafana endpoint (default: http://localhost:3000)

Monitoring Components:
  - System metrics (CPU, memory, disk, load)
  - Service health (API Gateway, Prediction Engine, Database, Redis)
  - Application performance (response times, throughput)
  - Network connectivity
  - Business metrics (if available)

Output:
  - HTML performance reports
  - JSON metrics data
  - Alert notifications (Slack/Email)
  - Dashboard updates

EOF
}

# =============================================================================
# EXECUTE
# =============================================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
