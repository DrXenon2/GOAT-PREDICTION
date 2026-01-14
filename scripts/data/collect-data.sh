#!/bin/bash

# Goat Prediction Ultimate - Data Collection Script
# Version: 2.0.0
# Author: Goat Prediction Team
# Description: Automated sports data collection from multiple sources

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$PROJECT_ROOT/config"
DATA_DIR="$PROJECT_ROOT/data"
LOGS_DIR="$PROJECT_ROOT/logs/data-collection"
BACKUP_DIR="$PROJECT_ROOT/.backups/data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOGS_DIR/collection_$TIMESTAMP.log"

# API Keys (load from environment or config)
API_KEYS=(
    "STATSBOMB_API_KEY"
    "OPTA_API_KEY" 
    "SPORTRADAR_API_KEY"
    "BETFAIR_API_KEY"
    "PINNACLE_API_KEY"
    "TWITTER_API_KEY"
    "NEWSAPI_API_KEY"
    "OPENWEATHER_API_KEY"
)

# Sports to collect
SPORTS=("football" "basketball" "tennis" "baseball" "rugby" "esports")

# Data sources configuration
declare -A DATA_SOURCES=(
    ["stats"]="StatsBomb,Opta,SportRadar,Wyscout,InStat"
    ["odds"]="Betfair,Pinnacle,Bet365,WilliamHill,Smarkets,Matchbook"
    ["news"]="NewsAPI,BBC,ESPN,GoogleNews"
    ["social"]="Twitter,Reddit"
    ["weather"]="OpenWeather,AccuWeather,Weather.com"
    ["injury"]="PremierInjuries,NBAInjuryReport"
)

# Parse command line arguments
VERBOSE=false
DRY_RUN=false
PARALLEL=true
BACKUP_ENABLED=true
CLEANUP_OLD=true
DAYS_TO_KEEP=30
SPORT_FILTER=""
DATA_TYPE="all"
START_DATE=""
END_DATE=""
FORCE_UPDATE=false
MAX_RETRIES=3
RETRY_DELAY=5

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${MAGENTA}"
    echo "================================================"
    echo "   GOAT PREDICTION ULTIMATE - DATA COLLECTION   "
    echo "================================================"
    echo -e "${NC}"
}

print_footer() {
    echo -e "${CYAN}"
    echo "================================================"
    echo "         DATA COLLECTION COMPLETE               "
    echo "================================================"
    echo -e "${NC}"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
  -h, --help                  Show this help message
  -v, --verbose               Enable verbose output
  -d, --dry-run               Dry run - don't actually collect data
  -s, --sport SPORT           Filter by sport (comma-separated)
  -t, --type TYPE             Data type to collect: all, stats, odds, news, social, weather
  --start-date DATE           Start date (YYYY-MM-DD)
  --end-date DATE             End date (YYYY-MM-DD)
  --no-backup                 Disable backup before collection
  --no-parallel               Run collection sequentially
  --force                     Force update even if data exists
  --max-retries NUM           Maximum retry attempts (default: 3)
  --retry-delay SEC           Delay between retries in seconds (default: 5)
  --cleanup-old DAYS          Cleanup data older than DAYS (default: 30)
  --no-cleanup               Disable cleanup of old data

Examples:
  $0                          # Collect all data for all sports
  $0 -s football,basketball   # Collect data for specific sports
  $0 -t odds --start-date 2024-01-01 --end-date 2024-01-07
  $0 --dry-run --verbose      # Dry run with verbose output
  $0 --force --no-backup      # Force update without backup

Supported Sports: ${SPORTS[*]}
Data Sources: ${!DATA_SOURCES[*]}
EOF
}

# Function to parse arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -s|--sport)
                SPORT_FILTER="$2"
                shift 2
                ;;
            -t|--type)
                DATA_TYPE="$2"
                shift 2
                ;;
            --start-date)
                START_DATE="$2"
                shift 2
                ;;
            --end-date)
                END_DATE="$2"
                shift 2
                ;;
            --no-backup)
                BACKUP_ENABLED=false
                shift
                ;;
            --no-parallel)
                PARALLEL=false
                shift
                ;;
            --force)
                FORCE_UPDATE=true
                shift
                ;;
            --max-retries)
                MAX_RETRIES="$2"
                shift 2
                ;;
            --retry-delay)
                RETRY_DELAY="$2"
                shift 2
                ;;
            --cleanup-old)
                CLEANUP_OLD=true
                DAYS_TO_KEEP="$2"
                shift 2
                ;;
            --no-cleanup)
                CLEANUP_OLD=false
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Function to validate date format
validate_date() {
    local date=$1
    if ! [[ $date =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        print_error "Invalid date format: $date. Use YYYY-MM-DD"
        return 1
    fi
    
    # Check if date is valid
    if ! date -d "$date" >/dev/null 2>&1; then
        print_error "Invalid date: $date"
        return 1
    fi
    
    return 0
}

# Function to check required tools
check_requirements() {
    print_info "Checking requirements..."
    
    local missing_tools=()
    
    # Check for required commands
    for cmd in python3 docker curl jq; do
        if ! command -v $cmd &> /dev/null; then
            missing_tools+=("$cmd")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_info "Please install missing tools and try again."
        exit 1
    fi
    
    # Check Python version
    local python_version=$(python3 --version | cut -d' ' -f2)
    if [[ $(echo "$python_version 3.11.0" | tr " " "\n" | sort -V | head -n1) != "3.11.0" ]]; then
        print_warning "Python version $python_version detected, 3.11+ recommended"
    fi
    
    # Check Docker
    if ! docker info &> /dev/null; then
        print_warning "Docker daemon not running. Some features may not work."
    fi
    
    print_success "Requirements check passed"
}

# Function to load configuration
load_config() {
    print_info "Loading configuration..."
    
    # Create directories if they don't exist
    mkdir -p "$DATA_DIR/raw" "$DATA_DIR/processed" "$DATA_DIR/cache"
    mkdir -p "$LOGS_DIR" "$BACKUP_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Load environment variables
    if [ -f "$PROJECT_ROOT/.env.local" ]; then
        source "$PROJECT_ROOT/.env.local"
        print_info "Loaded environment from .env.local"
    elif [ -f "$PROJECT_ROOT/.env" ]; then
        source "$PROJECT_ROOT/.env"
        print_info "Loaded environment from .env"
    else
        print_warning "No environment file found. Using default configuration."
    fi
    
    # Check for required API keys
    local missing_keys=()
    for key in "${API_KEYS[@]}"; do
        if [ -z "${!key:-}" ]; then
            missing_keys+=("$key")
        fi
    done
    
    if [ ${#missing_keys[@]} -gt 0 ]; then
        print_warning "Missing API keys: ${missing_keys[*]}"
        print_info "Some data sources may not be available."
    fi
    
    # Validate dates
    if [ -n "$START_DATE" ]; then
        validate_date "$START_DATE" || exit 1
    fi
    
    if [ -n "$END_DATE" ]; then
        validate_date "$END_DATE" || exit 1
    fi
    
    # Set default dates if not provided
    if [ -z "$START_DATE" ]; then
        START_DATE=$(date -d "30 days ago" +%Y-%m-%d)
    fi
    
    if [ -z "$END_DATE" ]; then
        END_DATE=$(date +%Y-%m-%d)
    fi
    
    # Validate sport filter
    if [ -n "$SPORT_FILTER" ]; then
        IFS=',' read -ra FILTERED_SPORTS <<< "$SPORT_FILTER"
        SPORTS=("${FILTERED_SPORTS[@]}")
        
        # Validate each sport
        for sport in "${SPORTS[@]}"; do
            if [[ ! " football basketball tennis baseball rugby esports " =~ " $sport " ]]; then
                print_error "Unsupported sport: $sport"
                exit 1
            fi
        done
    fi
    
    # Validate data type
    if [[ ! " all stats odds news social weather " =~ " $DATA_TYPE " ]]; then
        print_error "Invalid data type: $DATA_TYPE"
        usage
        exit 1
    fi
    
    print_success "Configuration loaded successfully"
}

# Function to backup existing data
backup_data() {
    if [ "$BACKUP_ENABLED" = false ]; then
        print_info "Backup disabled"
        return 0
    fi
    
    print_info "Backing up existing data..."
    
    local backup_path="$BACKUP_DIR/data_backup_$TIMESTAMP.tar.gz"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would backup to: $backup_path"
        return 0
    fi
    
    # Create backup
    if tar -czf "$backup_path" -C "$DATA_DIR" raw processed cache 2>/dev/null; then
        print_success "Backup created: $backup_path ($(du -h "$backup_path" | cut -f1))"
        
        # Remove old backups (keep last 7)
        local old_backups=$(find "$BACKUP_DIR" -name "data_backup_*.tar.gz" -type f | sort -r | tail -n +8)
        if [ -n "$old_backups" ]; then
            echo "$old_backups" | xargs rm -f
            print_info "Removed old backups"
        fi
    else
        print_error "Failed to create backup"
        return 1
    fi
}

# Function to cleanup old data
cleanup_old_data() {
    if [ "$CLEANUP_OLD" = false ]; then
        print_info "Cleanup disabled"
        return 0
    fi
    
    print_info "Cleaning up data older than $DAYS_TO_KEEP days..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would cleanup data older than $DAYS_TO_KEEP days"
        return 0
    fi
    
    # Cleanup raw data
    local cleaned=0
    for sport_dir in "$DATA_DIR/raw"/*/; do
        if [ -d "$sport_dir" ]; then
            local files_to_remove=$(find "$sport_dir" -type f -name "*.json" -o -name "*.csv" -mtime +$DAYS_TO_KEEP)
            if [ -n "$files_to_remove" ]; then
                echo "$files_to_remove" | xargs rm -f
                cleaned=$((cleaned + $(echo "$files_to_remove" | wc -l)))
            fi
        fi
    done
    
    if [ $cleaned -gt 0 ]; then
        print_success "Cleaned up $cleaned old data files"
    else
        print_info "No old data to clean up"
    fi
}

# Function to run data collection with retries
run_collection() {
    local sport=$1
    local data_type=$2
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        print_info "Collecting $data_type data for $sport (Attempt $attempt/$MAX_RETRIES)..."
        
        if [ "$DRY_RUN" = true ]; then
            print_info "[DRY RUN] Would collect $data_type data for $sport"
            return 0
        fi
        
        # Run the collection command
        if collect_data "$sport" "$data_type"; then
            print_success "Successfully collected $data_type data for $sport"
            return 0
        else
            print_error "Failed to collect $data_type data for $sport"
            
            if [ $attempt -lt $MAX_RETRIES ]; then
                print_info "Retrying in $RETRY_DELAY seconds..."
                sleep $RETRY_DELAY
                attempt=$((attempt + 1))
            else
                print_error "Max retries reached for $sport $data_type"
                return 1
            fi
        fi
    done
}

# Function to collect data for specific sport and type
collect_data() {
    local sport=$1
    local data_type=$2
    
    # Define output directory
    local output_dir="$DATA_DIR/raw/$sport/$data_type/$(date +%Y/%m/%d)"
    mkdir -p "$output_dir"
    
    # Define log file for this collection
    local collection_log="$LOGS_DIR/${sport}_${data_type}_${TIMESTAMP}.log"
    
    # Build command arguments
    local cmd_args=()
    cmd_args+=("--sport" "$sport")
    cmd_args+=("--data-type" "$data_type")
    cmd_args+=("--output-dir" "$output_dir")
    cmd_args+=("--start-date" "$START_DATE")
    cmd_args+=("--end-date" "$END_DATE")
    cmd_args+=("--log-file" "$collection_log")
    
    if [ "$VERBOSE" = true ]; then
        cmd_args+=("--verbose")
    fi
    
    if [ "$FORCE_UPDATE" = true ]; then
        cmd_args+=("--force")
    fi
    
    # Execute collection based on data type
    case $data_type in
        "stats")
            python3 "$PROJECT_ROOT/backend/prediction-engine/src/data/collectors/football/statsbomb_collector.py" "${cmd_args[@]}" 2>&1 | tee -a "$LOG_FILE"
            ;;
        "odds")
            python3 "$PROJECT_ROOT/backend/prediction-engine/src/data/collectors/odds/betfair_collector.py" "${cmd_args[@]}" 2>&1 | tee -a "$LOG_FILE"
            ;;
        "news")
            python3 "$PROJECT_ROOT/backend/prediction-engine/src/data/collectors/news/newsapi_collector.py" "${cmd_args[@]}" 2>&1 | tee -a "$LOG_FILE"
            ;;
        "social")
            python3 "$PROJECT_ROOT/backend/prediction-engine/src/data/collectors/social/twitter_collector.py" "${cmd_args[@]}" 2>&1 | tee -a "$LOG_FILE"
            ;;
        "weather")
            python3 "$PROJECT_ROOT/backend/prediction-engine/src/data/collectors/weather/openweather_collector.py" "${cmd_args[@]}" 2>&1 | tee -a "$LOG_FILE"
            ;;
        *)
            # Generic collector
            python3 "$PROJECT_ROOT/backend/prediction-engine/src/data/collectors/base_collector.py" "${cmd_args[@]}" 2>&1 | tee -a "$LOG_FILE"
            ;;
    esac
    
    # Check if collection was successful
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        # Verify that files were created
        local file_count=$(find "$output_dir" -type f -name "*.json" -o -name "*.csv" 2>/dev/null | wc -l)
        if [ $file_count -gt 0 ]; then
            print_info "Collected $file_count files for $sport $data_type"
            return 0
        else
            print_warning "No files collected for $sport $data_type"
            return 1
        fi
    else
        return 1
    fi
}

# Function to process collected data
process_data() {
    print_info "Processing collected data..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would process data"
        return 0
    fi
    
    # Run data processing pipeline
    python3 "$PROJECT_ROOT/backend/prediction-engine/src/data/processors/pipeline.py" \
        --input-dir "$DATA_DIR/raw" \
        --output-dir "$DATA_DIR/processed" \
        --log-file "$LOGS_DIR/processing_$TIMESTAMP.log" \
        ${VERBOSE:+--verbose} 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_success "Data processing completed"
        
        # Generate processing report
        generate_report
    else
        print_error "Data processing failed"
        return 1
    fi
}

# Function to generate collection report
generate_report() {
    print_info "Generating collection report..."
    
    local report_file="$LOGS_DIR/report_$TIMESTAMP.txt"
    
    cat > "$report_file" << EOF
GOAT PREDICTION ULTIMATE - DATA COLLECTION REPORT
==================================================
Collection Time: $(date)
Duration: $SECONDS seconds
Environment: $(uname -s) $(uname -r)
Python Version: $(python3 --version)
Script Version: 2.0.0

CONFIGURATION:
--------------
Sports Collected: ${SPORTS[*]}
Data Types: $DATA_TYPE
Date Range: $START_DATE to $END_DATE
Dry Run: $DRY_RUN
Force Update: $FORCE_UPDATE
Backup Enabled: $BACKUP_ENABLED
Parallel Collection: $PARALLEL

DATA COLLECTION SUMMARY:
------------------------
EOF
    
    # Count collected files by sport and type
    for sport in "${SPORTS[@]}"; do
        echo "" >> "$report_file"
        echo "$(echo $sport | tr '[:lower:]' '[:upper:]'):" >> "$report_file"
        echo "  Raw Data:" >> "$report_file"
        
        if [ "$DATA_TYPE" = "all" ]; then
            for type in "${!DATA_SOURCES[@]}"; do
                local count=$(find "$DATA_DIR/raw/$sport/$type" -type f -name "*.json" -o -name "*.csv" 2>/dev/null | wc -l)
                echo "    $type: $count files" >> "$report_file"
            done
        else
            local count=$(find "$DATA_DIR/raw/$sport/$DATA_TYPE" -type f -name "*.json" -o -name "*.csv" 2>/dev/null | wc -l)
            echo "    $DATA_TYPE: $count files" >> "$report_file"
        fi
        
        # Processed data
        echo "  Processed Data:" >> "$report_file"
        local processed_count=$(find "$DATA_DIR/processed/$sport" -type f -name "*.parquet" -o -name "*.feather" 2>/dev/null | wc -l)
        echo "    Total: $processed_count files" >> "$report_file"
    done
    
    # Disk usage
    echo "" >> "$report_file"
    echo "DISK USAGE:" >> "$report_file"
    echo "-----------" >> "$report_file"
    du -sh "$DATA_DIR"/raw "$DATA_DIR"/processed "$DATA_DIR"/cache >> "$report_file" 2>/dev/null || true
    
    # Log files
    echo "" >> "$report_file"
    echo "LOG FILES:" >> "$report_file"
    echo "----------" >> "$report_file"
    ls -la "$LOGS_DIR"/*"$TIMESTAMP"*.log 2>/dev/null | awk '{print $5 " " $9}' >> "$report_file" || echo "No log files" >> "$report_file"
    
    # Backup info
    if [ "$BACKUP_ENABLED" = true ]; then
        echo "" >> "$report_file"
        echo "BACKUPS:" >> "$report_file"
        echo "--------" >> "$report_file"
        ls -la "$BACKUP_DIR"/data_backup_*.tar.gz 2>/dev/null | tail -5 >> "$report_file" || echo "No backups" >> "$report_file"
    fi
    
    print_success "Report generated: $report_file"
}

# Function to monitor collection progress
monitor_progress() {
    if [ "$VERBOSE" = false ] && [ "$DRY_RUN" = false ]; then
        local total_tasks=$(( ${#SPORTS[@]} * $(if [ "$DATA_TYPE" = "all" ]; then echo ${#DATA_SOURCES[@]}; else echo 1; fi) ))
        local completed_tasks=0
        
        while [ $completed_tasks -lt $total_tasks ]; do
            # Simple progress bar
            local percentage=$(( completed_tasks * 100 / total_tasks ))
            local bar_length=50
            local filled=$(( percentage * bar_length / 100 ))
            local bar=$(printf "%0.s#" $(seq 1 $filled))
            local empty=$(printf "%0.s-" $(seq 1 $((bar_length - filled))))
            
            echo -ne "\rProgress: [$bar$empty] $percentage% ($completed_tasks/$total_tasks)"
            sleep 1
            
            # Update completed tasks (simplified)
            completed_tasks=$(find "$DATA_DIR/raw" -type f -name "*.json" -o -name "*.csv" 2>/dev/null | wc -l)
        done
        
        echo -e "\n"
    fi
}

# Function to validate collected data
validate_data() {
    print_info "Validating collected data..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would validate data"
        return 0
    fi
    
    # Run data validation
    python3 "$PROJECT_ROOT/backend/prediction-engine/src/data/validators/data_validator.py" \
        --data-dir "$DATA_DIR/raw" \
        --report-file "$LOGS_DIR/validation_$TIMESTAMP.json" \
        ${VERBOSE:+--verbose} 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_success "Data validation completed"
        
        # Check validation results
        if [ -f "$LOGS_DIR/validation_$TIMESTAMP.json" ]; then
            local errors=$(jq '.errors | length' "$LOGS_DIR/validation_$TIMESTAMP.json" 2>/dev/null || echo "0")
            local warnings=$(jq '.warnings | length' "$LOGS_DIR/validation_$TIMESTAMP.json" 2>/dev/null || echo "0")
            
            if [ "$errors" -gt 0 ]; then
                print_error "Found $errors errors in collected data"
                return 1
            elif [ "$warnings" -gt 0 ]; then
                print_warning "Found $warnings warnings in collected data"
            else
                print_success "No issues found in collected data"
            fi
        fi
    else
        print_error "Data validation failed"
        return 1
    fi
}

# Function to send notification
send_notification() {
    local status=$1
    local message=$2
    
    # Check if notifications are enabled
    if [ -z "${NOTIFICATION_WEBHOOK:-}" ]; then
        return 0
    fi
    
    local payload=$(cat << EOF
{
    "project": "Goat Prediction Ultimate",
    "environment": "$ENV_SUFFIX",
    "status": "$status",
    "message": "$message",
    "timestamp": "$(date -Iseconds)",
    "duration": "$SECONDS seconds",
    "log_file": "$LOG_FILE"
}
EOF
)
    
    if [ "$DRY_RUN" = false ]; then
        curl -s -X POST -H "Content-Type: application/json" \
            -d "$payload" "$NOTIFICATION_WEBHOOK" >/dev/null 2>&1 || true
    fi
}

# Main execution function
main() {
    # Start timer
    SECONDS=0
    
    # Parse arguments
    parse_arguments "$@"
    
    # Print header
    print_header
    
    # Setup logging
    exec > >(tee -a "$LOG_FILE")
    exec 2>&1
    
    print_info "Starting data collection at $(date)"
    print_info "Log file: $LOG_FILE"
    
    # Check requirements
    check_requirements
    
    # Load configuration
    load_config
    
    # Backup existing data
    backup_data
    
    # Cleanup old data
    cleanup_old_data
    
    # Determine data types to collect
    local data_types_to_collect=()
    if [ "$DATA_TYPE" = "all" ]; then
        data_types_to_collect=("${!DATA_SOURCES[@]}")
    else
        data_types_to_collect=("$DATA_TYPE")
    fi
    
    # Collect data
    local collection_errors=0
    local collection_tasks=()
    
    for sport in "${SPORTS[@]}"; do
        for data_type in "${data_types_to_collect[@]}"; do
            if [ "$PARALLEL" = true ]; then
                # Run in background for parallel execution
                (run_collection "$sport" "$data_type" || echo "ERROR:$sport:$data_type" >> "$LOGS_DIR/errors_$TIMESTAMP.txt") &
                collection_tasks+=($!)
            else
                # Run sequentially
                if ! run_collection "$sport" "$data_type"; then
                    collection_errors=$((collection_errors + 1))
                    echo "$sport:$data_type" >> "$LOGS_DIR/errors_$TIMESTAMP.txt"
                fi
            fi
        done
    done
    
    # Wait for parallel tasks to complete
    if [ "$PARALLEL" = true ]; then
        print_info "Waiting for parallel collection tasks to complete..."
        for task in "${collection_tasks[@]}"; do
            wait "$task" || collection_errors=$((collection_errors + 1))
        done
    fi
    
    # Monitor progress (if not verbose)
    monitor_progress &
    local monitor_pid=$!
    
    # Wait for monitoring to complete
    wait $monitor_pid 2>/dev/null || true
    
    # Check for collection errors
    if [ $collection_errors -gt 0 ]; then
        print_error "Collection completed with $collection_errors errors"
        
        if [ -f "$LOGS_DIR/errors_$TIMESTAMP.txt" ]; then
            print_info "Failed collections:"
            cat "$LOGS_DIR/errors_$TIMESTAMP.txt"
        fi
    else
        print_success "All data collected successfully"
    fi
    
    # Process collected data (if any successful collections)
    if [ "$DRY_RUN" = false ] && [ $collection_errors -lt ${#SPORTS[@]} ]; then
        if ! process_data; then
            print_error "Data processing failed"
            collection_errors=$((collection_errors + 1))
        fi
        
        # Validate data
        if ! validate_data; then
            print_error "Data validation failed"
            collection_errors=$((collection_errors + 1))
        fi
    fi
    
    # Generate report
    generate_report
    
    # Calculate duration
    local duration=$SECONDS
    local hours=$((duration / 3600))
    local minutes=$(( (duration % 3600) / 60 ))
    local seconds=$((duration % 60))
    
    print_info "Total duration: ${hours}h ${minutes}m ${seconds}s"
    
    # Send notification
    if [ $collection_errors -eq 0 ]; then
        send_notification "success" "Data collection completed successfully in ${hours}h ${minutes}m ${seconds}s"
        print_footer
        exit 0
    else
        send_notification "error" "Data collection completed with $collection_errors errors"
        print_error "Data collection completed with errors"
        exit 1
    fi
}

# Function to handle script termination
cleanup() {
    local exit_code=$?
    
    # Kill background processes
    jobs -p | xargs kill -9 2>/dev/null || true
    
    # Final log message
    if [ $exit_code -eq 0 ]; then
        print_success "Script terminated successfully"
    else
        print_error "Script terminated with error code: $exit_code"
    fi
    
    exit $exit_code
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Run main function
main "$@"
