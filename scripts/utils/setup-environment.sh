#!/bin/bash

# 🐐 GOAT-PREDICTION ULTIMATE - ENVIRONMENT SETUP SCRIPT
# Version: 2.0.0
# Description: Complete environment setup and configuration for GOAT-PREDICTION platform
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

# Environment variables
ENVIRONMENT=${ENVIRONMENT:-"development"}
PLATFORM=${PLATFORM:-"auto"}  # auto, linux, macos, windows, docker, kubernetes
SETUP_MODE=${SETUP_MODE:-"complete"}  # minimal, standard, complete, custom
SKIP_CONFIRMATION=${SKIP_CONFIRMATION:-"false"}
FORCE_RECONFIGURE=${FORCE_RECONFIGURE:-"false"}
INSTALL_DEPENDENCIES=${INSTALL_DEPENDENCIES:-"true"}
CONFIGURE_SERVICES=${CONFIGURE_SERVICES:-"true"}
SETUP_SECURITY=${SETUP_SECURITY:-"true"}
GENERATE_CERTIFICATES=${GENERATE_CERTIFICATES:-"true"}
INITIALIZE_DATABASE=${INITIALIZE_DATABASE:-"true"}
VALIDATE_SETUP=${VALIDATE_SETUP:-"true"}

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
CONFIG_DIR="$ROOT_DIR/.config"
SECRETS_DIR="$ROOT_DIR/.secrets"
LOG_DIR="$ROOT_DIR/.logs/setup"
BACKUP_DIR="$ROOT_DIR/.backups/setup"
TEMP_DIR="/tmp/goat_setup_$(date +%Y%m%d_%H%M%S)"
ENV_DIR="$ROOT_DIR/env"

# Files
SETUP_LOG="$LOG_DIR/setup_$(date +%Y%m%d_%H%M%S).log"
ERROR_LOG="$LOG_DIR/errors_$(date +%Y%m%d_%H%M%S).log"
CONFIG_FILE="$CONFIG_DIR/setup.yaml"
ENV_FILE="$ROOT_DIR/.env.$ENVIRONMENT"
ENV_TEMPLATE="$ROOT_DIR/.env.example"
STATE_FILE="$LOG_DIR/setup_state_$(date +%Y%m%d_%H%M%S).json"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
REQUIREMENTS_DEV_FILE="$ROOT_DIR/requirements-dev.txt"
REQUIREMENTS_ML_FILE="$ROOT_DIR/requirements-ml.txt"
LOCK_FILE="/tmp/goat_setup.lock"

# User configuration
USER_ID=$(id -u)
USER_NAME=$(whoami)
HOSTNAME=$(hostname)
OS_TYPE="unknown"
OS_VERSION="unknown"
CPU_CORES=$(nproc)
TOTAL_MEMORY=$(free -g | awk '/^Mem:/{print $2}')
AVAILABLE_DISK=$(df -h / | awk 'NR==2{print $4}')

# Package managers
declare -A PACKAGE_MANAGERS=(
    ["apt-get"]="Debian/Ubuntu"
    ["yum"]="RHEL/CentOS"
    ["dnf"]="Fedora"
    ["pacman"]="Arch"
    ["brew"]="macOS"
    ["choco"]="Windows"
)

# =============================================================================
# FUNCTIONS
# =============================================================================

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$SETUP_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$SETUP_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$SETUP_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$SETUP_LOG" "$ERROR_LOG"
}

log_step() {
    echo -e "\n${PURPLE}========================================${NC}"
    echo -e "${CYAN}STEP: $1${NC}"
    echo -e "${PURPLE}========================================${NC}\n" | tee -a "$SETUP_LOG"
}

log_header() {
    echo -e "\n${WHITE}$1${NC}" | tee -a "$SETUP_LOG"
}

# Banner display
show_banner() {
    clear
    cat << "EOF"

    ██████╗  ██████╗  █████╗ ████████╗    ███████╗███████╗████████╗██╗   ██╗██████╗ 
    ██╔════╝ ██╔═══██╗██╔══██╗╚══██╔══╝    ██╔════╝██╔════╝╚══██╔══╝██║   ██║██╔══██╗
    ██║  ███╗██║   ██║███████║   ██║       ███████╗█████╗     ██║   ██║   ██║██████╔╝
    ██║   ██║██║   ██║██╔══██║   ██║       ╚════██║██╔══╝     ██║   ██║   ██║██╔═══╝ 
    ╚██████╔╝╚██████╔╝██║  ██║   ██║       ███████║███████╗   ██║   ╚██████╔╝██║     
    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝       ╚══════╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝     
    
    🐐 GOAT-PREDICTION ULTIMATE - ENVIRONMENT SETUP v2.0.0
    =============================================================================
    
EOF
    log_info "Starting environment setup for: $ENVIRONMENT"
    log_info "Setup mode: $SETUP_MODE | Platform: $PLATFORM"
    log_info "User: $USER_NAME@$HOSTNAME (UID: $USER_ID)"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites"
    
    # Check if running as root (warn but don't require)
    if [ "$USER_ID" -eq 0 ]; then
        log_warning "Running as root. It's recommended to run as a regular user."
        
        if [ "$SKIP_CONFIRMATION" != "true" ]; then
            read -p "Continue as root? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_error "Setup aborted by user"
                exit 1
            fi
        fi
    fi
    
    # Check disk space
    local disk_space=$(df -k / | awk 'NR==2{print $4}')
    local min_space=$((50 * 1024 * 1024))  # 50GB minimum
    
    if [ "$disk_space" -lt "$min_space" ]; then
        log_error "Insufficient disk space. Available: ${disk_space}KB, Required: ${min_space}KB"
        log_error "Please free up disk space and try again."
        exit 1
    fi
    
    # Check memory
    if [ "$TOTAL_MEMORY" -lt 8 ]; then
        log_warning "Low memory detected: ${TOTAL_MEMORY}GB. 16GB+ recommended for optimal performance."
    fi
    
    # Check CPU cores
    if [ "$CPU_CORES" -lt 4 ]; then
        log_warning "Limited CPU cores detected: ${CPU_CORES}. 8+ cores recommended for ML workloads."
    fi
    
    log_success "Basic prerequisites check passed"
}

# Detect platform
detect_platform() {
    log_step "Detecting platform"
    
    if [ "$PLATFORM" != "auto" ]; then
        log_info "Using specified platform: $PLATFORM"
        OS_TYPE="$PLATFORM"
        return 0
    fi
    
    # Detect operating system
    case "$(uname -s)" in
        Linux*)
            OS_TYPE="linux"
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                OS_VERSION="$NAME $VERSION"
                
                # Detect distribution
                case "$ID" in
                    ubuntu|debian)
                        OS_TYPE="ubuntu"
                        ;;
                    centos|rhel|fedora)
                        OS_TYPE="centos"
                        ;;
                    arch)
                        OS_TYPE="arch"
                        ;;
                    alpine)
                        OS_TYPE="alpine"
                        ;;
                    *)
                        OS_TYPE="linux"
                        ;;
                esac
            fi
            ;;
        Darwin*)
            OS_TYPE="macos"
            OS_VERSION="$(sw_vers -productName) $(sw_vers -productVersion)"
            ;;
        CYGWIN*|MINGW32*|MSYS*|MINGW*)
            OS_TYPE="windows"
            OS_VERSION="Windows"
            ;;
        *)
            OS_TYPE="unknown"
            OS_VERSION="unknown"
            ;;
    esac
    
    # Detect container environment
    if [ -f /.dockerenv ]; then
        OS_TYPE="docker"
        log_info "Running inside Docker container"
    fi
    
    # Detect Kubernetes
    if [ -n "${KUBERNETES_SERVICE_HOST:-}" ]; then
        OS_TYPE="kubernetes"
        log_info "Running inside Kubernetes cluster"
    fi
    
    log_success "Platform detected: $OS_TYPE ($OS_VERSION)"
    log_info "CPU Cores: $CPU_CORES | Memory: ${TOTAL_MEMORY}GB | Disk: $AVAILABLE_DISK available"
}

# Check lock file
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        local process_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
        
        if [ "$process_name" = "setup-environment.sh" ] || [ "$process_name" = "bash" ]; then
            log_error "Setup is already running (PID: $pid)"
            
            if [ "$FORCE_RECONFIGURE" = "true" ]; then
                log_warning "Forcing reconfiguration, killing previous setup..."
                kill -9 "$pid" 2>/dev/null || true
                rm -f "$LOCK_FILE"
            else
                exit 1
            fi
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

# Create directory structure
create_directory_structure() {
    log_step "Creating directory structure"
    
    # Main directories
    local directories=(
        "$CONFIG_DIR"
        "$SECRETS_DIR"
        "$LOG_DIR"
        "$BACKUP_DIR"
        "$ENV_DIR"
        "$TEMP_DIR"
        "$ROOT_DIR/.cache"
        "$ROOT_DIR/.tmp"
        "$ROOT_DIR/.vscode"
        "$ROOT_DIR/data"
        "$ROOT_DIR/data/raw"
        "$ROOT_DIR/data/processed"
        "$ROOT_DIR/data/cache"
        "$ROOT_DIR/models"
        "$ROOT_DIR/deployments"
        "$ROOT_DIR/backups"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        else
            log_info "Directory exists: $dir"
        fi
    done
    
    # Set secure permissions for secrets directory
    chmod 700 "$SECRETS_DIR"
    
    log_success "Directory structure created"
}

# Backup existing configuration
backup_existing_config() {
    log_step "Backing up existing configuration"
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup environment files
    if ls "$ROOT_DIR"/.env* 2>/dev/null; then
        cp -r "$ROOT_DIR"/.env* "$backup_path/" 2>/dev/null || true
        log_info "Backed up environment files"
    fi
    
    # Backup configuration directory
    if [ -d "$CONFIG_DIR" ]; then
        cp -r "$CONFIG_DIR" "$backup_path/config_old/" 2>/dev/null || true
        log_info "Backed up configuration directory"
    fi
    
    # Backup secrets (encrypted if possible)
    if [ -d "$SECRETS_DIR" ]; then
        tar -czf "$backup_path/secrets_backup.tar.gz" -C "$SECRETS_DIR" . 2>/dev/null || true
        log_info "Backed up secrets directory"
    fi
    
    if [ -d "$backup_path" ] && [ "$(ls -A "$backup_path" 2>/dev/null)" ]; then
        log_success "Backup created: $backup_path"
    else
        log_info "No existing configuration to backup"
    fi
}

# Detect package manager
detect_package_manager() {
    log_step "Detecting package manager"
    
    local detected_manager=""
    
    for manager in "${!PACKAGE_MANAGERS[@]}"; do
        if command -v "$manager" &> /dev/null; then
            detected_manager="$manager"
            log_info "Detected package manager: $manager (${PACKAGE_MANAGERS[$manager]})"
            break
        fi
    done
    
    if [ -z "$detected_manager" ]; then
        log_error "No supported package manager found"
        log_info "Supported managers: ${!PACKAGE_MANAGERS[*]}"
        return 1
    fi
    
    echo "$detected_manager"
}

# Install system dependencies
install_system_dependencies() {
    if [ "$INSTALL_DEPENDENCIES" != "true" ]; then
        log_info "Skipping system dependencies installation"
        return 0
    fi
    
    log_step "Installing system dependencies"
    
    local package_manager=$(detect_package_manager)
    local update_cmd=""
    local install_cmd=""
    
    case "$package_manager" in
        apt-get)
            update_cmd="sudo apt-get update -y"
            install_cmd="sudo apt-get install -y"
            ;;
        yum)
            update_cmd="sudo yum check-update -y || true"
            install_cmd="sudo yum install -y"
            ;;
        dnf)
            update_cmd="sudo dnf check-update -y || true"
            install_cmd="sudo dnf install -y"
            ;;
        pacman)
            update_cmd="sudo pacman -Sy"
            install_cmd="sudo pacman -S --noconfirm"
            ;;
        brew)
            update_cmd="brew update"
            install_cmd="brew install"
            ;;
        *)
            log_error "Unsupported package manager: $package_manager"
            return 1
            ;;
    esac
    
    # Define packages based on platform and setup mode
    local basic_packages=()
    local dev_packages=()
    local ml_packages=()
    local docker_packages=()
    
    case "$OS_TYPE" in
        ubuntu|debian|linux)
            basic_packages=(
                "curl"
                "wget"
                "git"
                "build-essential"
                "python3"
                "python3-pip"
                "python3-venv"
                "python3-dev"
                "libssl-dev"
                "libffi-dev"
                "ca-certificates"
                "software-properties-common"
                "apt-transport-https"
                "gnupg"
                "lsb-release"
            )
            
            dev_packages=(
                "nodejs"
                "npm"
                "postgresql-client"
                "redis-tools"
                "jq"
                "yq"
                "htop"
                "iotop"
                "nmon"
                "net-tools"
                "dnsutils"
                "tree"
                "unzip"
                "zip"
                "tmux"
                "vim"
                "nano"
            )
            
            ml_packages=(
                "libopenblas-dev"
                "liblapack-dev"
                "gfortran"
                "libhdf5-dev"
                "libatlas-base-dev"
                "libjasper-dev"
                "libqtgui4"
                "libqt4-test"
                "libavcodec-dev"
                "libavformat-dev"
                "libswscale-dev"
                "libtiff5-dev"
                "libjpeg-dev"
                "libpng-dev"
                "libgtk-3-dev"
            )
            
            docker_packages=(
                "docker.io"
                "docker-compose"
                "containerd.io"
            )
            ;;
            
        centos|rhel|fedora)
            basic_packages=(
                "curl"
                "wget"
                "git"
                "gcc"
                "gcc-c++"
                "make"
                "python3"
                "python3-pip"
                "python3-devel"
                "openssl-devel"
                "libffi-devel"
                "ca-certificates"
                "epel-release"
            )
            
            dev_packages=(
                "nodejs"
                "npm"
                "postgresql"
                "redis"
                "jq"
                "yq"
                "htop"
                "iotop"
                "nmon"
                "net-tools"
                "bind-utils"
                "tree"
                "unzip"
                "zip"
                "tmux"
                "vim"
                "nano"
            )
            
            ml_packages=(
                "openblas-devel"
                "lapack-devel"
                "gcc-gfortran"
                "hdf5-devel"
                "atlas-devel"
                "libjpeg-turbo-devel"
                "libpng-devel"
                "gtk3-devel"
            )
            
            docker_packages=(
                "docker"
                "docker-compose"
                "containerd"
            )
            ;;
            
        macos)
            log_info "Using Homebrew for macOS packages"
            
            # Install Homebrew if not present
            if ! command -v brew &> /dev/null; then
                log_info "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            basic_packages=(
                "curl"
                "wget"
                "git"
                "python3"
                "python@3.11"
                "openssl"
                "libffi"
            )
            
            dev_packages=(
                "node"
                "postgresql"
                "redis"
                "jq"
                "yq"
                "htop"
                "wget"
                "tree"
                "tmux"
                "vim"
                "nano"
            )
            
            ml_packages=(
                "openblas"
                "lapack"
                "hdf5"
                "jpeg"
                "libpng"
                "libtiff"
            )
            
            docker_packages=(
                "docker"
                "docker-compose"
            )
            ;;
            
        windows)
            log_info "Windows platform detected - some features may be limited"
            
            # Check for Chocolatey
            if ! command -v choco &> /dev/null; then
                log_info "Installing Chocolatey..."
                powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
            fi
            
            basic_packages=(
                "git"
                "python3"
                "curl"
                "wget"
                "openssl"
            )
            
            dev_packages=(
                "nodejs"
                "postgresql"
                "redis"
                "jq"
                "yq"
                "7zip"
                "vim"
                "nano"
            )
            ;;
            
        docker)
            log_info "Docker container detected - skipping system package installation"
            return 0
            ;;
            
        kubernetes)
            log_info "Kubernetes environment detected - skipping system package installation"
            return 0
            ;;
            
        *)
            log_error "Unsupported OS type: $OS_TYPE"
            return 1
            ;;
    esac
    
    # Install packages based on setup mode
    log_info "Installing packages for setup mode: $SETUP_MODE"
    
    # Update package lists
    log_info "Updating package lists..."
    if [ -n "$update_cmd" ]; then
        eval "$update_cmd" >> "$SETUP_LOG" 2>> "$ERROR_LOG" || log_warning "Package list update had issues"
    fi
    
    # Install basic packages
    if [ ${#basic_packages[@]} -gt 0 ]; then
        log_info "Installing basic packages..."
        for pkg in "${basic_packages[@]}"; do
            log_info "  - $pkg"
        done
        
        if [ "$package_manager" = "brew" ]; then
            $install_cmd "${basic_packages[@]}" >> "$SETUP_LOG" 2>> "$ERROR_LOG" || \
                log_warning "Some packages may have failed to install"
        else
            $install_cmd "${basic_packages[@]}" >> "$SETUP_LOG" 2>> "$ERROR_LOG" || \
                log_warning "Some packages may have failed to install"
        fi
    fi
    
    # Install dev packages for standard/complete modes
    if [[ "$SETUP_MODE" =~ ^(standard|complete|custom)$ ]] && [ ${#dev_packages[@]} -gt 0 ]; then
        log_info "Installing development packages..."
        for pkg in "${dev_packages[@]}"; do
            log_info "  - $pkg"
        done
        
        if [ "$package_manager" = "brew" ]; then
            $install_cmd "${dev_packages[@]}" >> "$SETUP_LOG" 2>> "$ERROR_LOG" || \
                log_warning "Some dev packages may have failed to install"
        else
            $install_cmd "${dev_packages[@]}" >> "$SETUP_LOG" 2>> "$ERROR_LOG" || \
                log_warning "Some dev packages may have failed to install"
        fi
    fi
    
    # Install ML packages for complete mode
    if [[ "$SETUP_MODE" =~ ^(complete|custom)$ ]] && [ ${#ml_packages[@]} -gt 0 ]; then
        log_info "Installing ML packages..."
        for pkg in "${ml_packages[@]}"; do
            log_info "  - $pkg"
        done
        
        if [ "$package_manager" = "brew" ]; then
            $install_cmd "${ml_packages[@]}" >> "$SETUP_LOG" 2>> "$ERROR_LOG" || \
                log_warning "Some ML packages may have failed to install"
        else
            $install_cmd "${ml_packages[@]}" >> "$SETUP_LOG" 2>> "$ERROR_LOG" || \
                log_warning "Some ML packages may have failed to install"
        fi
    fi
    
    # Install Docker for complete mode (except on Docker/Kubernetes)
    if [[ "$SETUP_MODE" =~ ^(complete|custom)$ ]] && [ ${#docker_packages[@]} -gt 0 ] && \
       [[ ! "$OS_TYPE" =~ ^(docker|kubernetes)$ ]]; then
        log_info "Installing Docker packages..."
        
        # Special handling for Docker installation
        case "$OS_TYPE" in
            ubuntu|debian)
                # Add Docker repository
                curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
                    sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg 2>> "$ERROR_LOG"
                
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
                    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
                    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
                
                sudo apt-get update >> "$SETUP_LOG" 2>> "$ERROR_LOG"
                $install_cmd "${docker_packages[@]}" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
                
                # Start Docker service
                sudo systemctl start docker >> "$SETUP_LOG" 2>> "$ERROR_LOG"
                sudo systemctl enable docker >> "$SETUP_LOG" 2>> "$ERROR_LOG"
                
                # Add user to docker group
                sudo usermod -aG docker "$USER_NAME" 2>> "$ERROR_LOG" || true
                ;;
                
            macos)
                # Docker Desktop for macOS
                log_info "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
                ;;
                
            *)
                $install_cmd "${docker_packages[@]}" >> "$SETUP_LOG" 2>> "$ERROR_LOG" || \
                    log_warning "Docker installation may have issues"
                ;;
        esac
    fi
    
    log_success "System dependencies installation completed"
}

# Setup Python environment
setup_python_environment() {
    log_step "Setting up Python environment"
    
    # Check Python version
    local python_version=$(python3 --version 2>/dev/null | cut -d' ' -f2)
    local required_version="3.9"
    
    if [ -z "$python_version" ]; then
        log_error "Python3 not found. Please install Python 3.9 or higher."
        return 1
    fi
    
    log_info "Python version: $python_version"
    
    # Compare versions
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        log_error "Python 3.9 or higher required. Found: $python_version"
        return 1
    fi
    
    # Create virtual environment
    local venv_dir="$ROOT_DIR/.venv"
    
    if [ ! -d "$venv_dir" ] || [ "$FORCE_RECONFIGURE" = "true" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv "$venv_dir" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
        
        if [ $? -eq 0 ]; then
            log_success "Virtual environment created: $venv_dir"
        else
            log_error "Failed to create virtual environment"
            return 1
        fi
    else
        log_info "Virtual environment already exists: $venv_dir"
    fi
    
    # Activate virtual environment
    log_info "Activating virtual environment..."
    source "$venv_dir/bin/activate"
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    
    # Install Python dependencies based on setup mode
    log_info "Installing Python dependencies..."
    
    # Install base requirements
    if [ -f "$REQUIREMENTS_FILE" ]; then
        log_info "Installing base requirements..."
        pip install -r "$REQUIREMENTS_FILE" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    fi
    
    # Install dev requirements for standard/complete modes
    if [[ "$SETUP_MODE" =~ ^(standard|complete|custom)$ ]] && [ -f "$REQUIREMENTS_DEV_FILE" ]; then
        log_info "Installing development requirements..."
        pip install -r "$REQUIREMENTS_DEV_FILE" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    fi
    
    # Install ML requirements for complete mode
    if [[ "$SETUP_MODE" =~ ^(complete|custom)$ ]] && [ -f "$REQUIREMENTS_ML_FILE" ]; then
        log_info "Installing ML requirements..."
        pip install -r "$REQUIREMENTS_ML_FILE" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    fi
    
    # Install additional packages based on setup mode
    local additional_packages=()
    
    case "$SETUP_MODE" in
        minimal)
            additional_packages=(
                "fastapi"
                "uvicorn"
                "pydantic"
                "sqlalchemy"
                "psycopg2-binary"
                "redis"
                "python-dotenv"
            )
            ;;
        standard)
            additional_packages=(
                "pandas"
                "numpy"
                "scikit-learn"
                "scipy"
                "matplotlib"
                "seaborn"
                "jupyter"
                "notebook"
                "black"
                "flake8"
                "mypy"
                "pytest"
                "pytest-cov"
            )
            ;;
        complete)
            additional_packages=(
                "torch"
                "torchvision"
                "tensorflow"
                "xgboost"
                "lightgbm"
                "catboost"
                "optuna"
                "mlflow"
                "prefect"
                "dask"
                "ray"
                "streamlit"
                "gradio"
            )
            ;;
    esac
    
    if [ ${#additional_packages[@]} -gt 0 ]; then
        log_info "Installing additional packages for $SETUP_MODE mode..."
        pip install "${additional_packages[@]}" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    fi
    
    # Verify installation
    log_info "Verifying Python package installation..."
    pip list >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    
    log_success "Python environment setup completed"
}

# Setup Node.js environment
setup_node_environment() {
    if [[ ! "$SETUP_MODE" =~ ^(standard|complete|custom)$ ]]; then
        log_info "Skipping Node.js setup (not needed for minimal mode)"
        return 0
    fi
    
    log_step "Setting up Node.js environment"
    
    # Check Node.js installation
    if ! command -v node &> /dev/null; then
        log_error "Node.js not found. Please install Node.js 16 or higher."
        return 1
    fi
    
    local node_version=$(node --version)
    local npm_version=$(npm --version)
    
    log_info "Node.js version: $node_version"
    log_info "npm version: $npm_version"
    
    # Check Node.js version
    local required_node_version="16.0.0"
    local current_node_version=$(echo "$node_version" | sed 's/v//')
    
    if [ "$(printf '%s\n' "$required_node_version" "$current_node_version" | sort -V | head -n1)" != "$required_node_version" ]; then
        log_error "Node.js 16 or higher required. Found: $node_version"
        return 1
    fi
    
    # Install npm packages
    local frontend_dir="$ROOT_DIR/frontend/web-app"
    
    if [ -d "$frontend_dir" ] && [ -f "$frontend_dir/package.json" ]; then
        log_info "Installing Node.js dependencies..."
        
        cd "$frontend_dir"
        
        # Install dependencies
        npm install >> "$SETUP_LOG" 2>> "$ERROR_LOG"
        
        # Install dev dependencies for complete mode
        if [[ "$SETUP_MODE" =~ ^(complete|custom)$ ]]; then
            log_info "Installing dev dependencies..."
            npm install --only=dev >> "$SETUP_LOG" 2>> "$ERROR_LOG"
        fi
        
        # Build if production
        if [ "$ENVIRONMENT" = "production" ]; then
            log_info "Building for production..."
            npm run build >> "$SETUP_LOG" 2>> "$ERROR_LOG"
        fi
        
        cd - > /dev/null
    else
        log_info "Frontend directory not found, skipping Node.js setup"
    fi
    
    log_success "Node.js environment setup completed"
}

# Generate environment configuration
generate_environment_config() {
    log_step "Generating environment configuration"
    
    # Check if environment file already exists
    if [ -f "$ENV_FILE" ] && [ "$FORCE_RECONFIGURE" != "true" ]; then
        if [ "$SKIP_CONFIRMATION" = "true" ]; then
            log_info "Environment file exists: $ENV_FILE"
            log_info "Using existing configuration (use --force to regenerate)"
            return 0
        else
            read -p "Environment file $ENV_FILE exists. Regenerate? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Using existing environment file"
                return 0
            fi
        fi
    fi
    
    # Load template if exists
    local env_content=""
    
    if [ -f "$ENV_TEMPLATE" ]; then
        env_content=$(cat "$ENV_TEMPLATE")
        log_info "Loaded template from: $ENV_TEMPLATE"
    else
        # Create basic template
        env_content=$(cat << 'EOF'
# 🐐 GOAT-PREDICTION Configuration
# Environment: ${ENVIRONMENT}
# Generated: $(date)

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

# Application
APP_NAME="GOAT-PREDICTION"
APP_VERSION="2.0.0"
APP_ENV="${ENVIRONMENT}"
APP_DEBUG="false"
APP_URL="http://localhost:3000"
APP_TIMEZONE="UTC"

# Security
SECRET_KEY="${SECRET_KEY}"
JWT_SECRET_KEY="${JWT_SECRET_KEY}"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API
API_PREFIX="/api"
API_VERSION="v1"
API_DOCS_ENABLED="true"
API_RATE_LIMIT_ENABLED="true"
API_RATE_LIMIT_PER_MINUTE=60

# =============================================================================
# DATABASE SETTINGS
# =============================================================================

# PostgreSQL
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
DB_HOST="localhost"
DB_PORT=5432
DB_NAME="goat_prediction_${ENVIRONMENT}"
DB_USER="goat_user"
DB_PASSWORD="${DB_PASSWORD}"

# Redis
REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}"
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD="${REDIS_PASSWORD}"
REDIS_SSL="false"

# =============================================================================
# ML & AI SETTINGS
# =============================================================================

# Model Settings
ML_MODEL_DIR="./models"
ML_CACHE_DIR="./.cache/ml"
ML_LOG_LEVEL="INFO"
ML_BATCH_SIZE=32
ML_DEVICE="auto"  # auto, cpu, cuda, mps

# Feature Store
FEATURE_STORE_TYPE="feast"  # feast, hopsworks, custom
FEATURE_STORE_REGISTRY="./feature_store"
FEATURE_STORE_HOST="localhost"
FEATURE_STORE_PORT=6566

# =============================================================================
# THIRD-PARTY SERVICES
# =============================================================================

# Supabase
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-key"
SUPABASE_SERVICE_KEY="your-service-key"

# Sports Data APIs
STATSBOMB_API_KEY=""
OPTA_API_KEY=""
SPORTRADAR_API_KEY=""

# Betting APIs
BETFAIR_API_KEY=""
PINNACLE_API_KEY=""
BET365_API_KEY=""

# =============================================================================
# MONITORING & LOGGING
# =============================================================================

# Logging
LOG_LEVEL="INFO"
LOG_FORMAT="json"
LOG_FILE="./logs/app.log"
LOG_ROTATION_SIZE="100MB"
LOG_RETENTION_DAYS=30

# Monitoring
PROMETHEUS_ENABLED="true"
PROMETHEUS_PORT=9090
GRAFANA_ENABLED="true"
GRAFANA_PORT=3000
SENTRY_DSN=""

# =============================================================================
# PERFORMANCE SETTINGS
# =============================================================================

# Server
UVICORN_WORKERS=${UVICORN_WORKERS}
UVICORN_HOST="0.0.0.0"
UVICORN_PORT=8000
UVICORN_RELOAD="false"

# Cache
CACHE_TYPE="redis"  # redis, memory, filesystem
CACHE_TTL_SECONDS=300
CACHE_MAX_SIZE_MB=1024

# =============================================================================
# BUSINESS SETTINGS
# =============================================================================

# Betting
BETTING_ENABLED="true"
BETTING_MIN_STAKE=1.0
BETTING_MAX_STAKE=1000.0
BETTING_DEFAULT_BANKROLL=10000.0
BETTING_KELLY_FRACTION=0.5

# Predictions
PREDICTION_CONFIDENCE_THRESHOLD=0.6
PREDICTION_UPDATE_INTERVAL=60
PREDICTION_BATCH_SIZE=100

# =============================================================================
# DEVELOPMENT SETTINGS
# =============================================================================

# Debug (only for development)
if [ "$APP_ENV" = "development" ]; then
    APP_DEBUG="true"
    API_DOCS_ENABLED="true"
    UVICORN_RELOAD="true"
    LOG_LEVEL="DEBUG"
fi

# Production overrides
if [ "$APP_ENV" = "production" ]; then
    APP_DEBUG="false"
    UVICORN_RELOAD="false"
    LOG_LEVEL="INFO"
    CACHE_TYPE="redis"
fi
EOF
        )
    fi
    
    # Generate secure values
    local secret_key=$(openssl rand -hex 32 2>/dev/null || echo "dev-secret-key-change-in-production")
    local jwt_secret=$(openssl rand -hex 32 2>/dev/null || echo "dev-jwt-secret-change-in-production")
    local db_password=$(openssl rand -hex 16 2>/dev/null || echo "dev_db_password")
    local redis_password=$(openssl rand -hex 16 2>/dev/null || echo "dev_redis_password")
    
    # Calculate workers based on CPU cores
    local uvicorn_workers=$((CPU_CORES * 2 + 1))
    
    # Replace variables in template
    env_content=$(echo "$env_content" | sed \
        -e "s|\${ENVIRONMENT}|$ENVIRONMENT|g" \
        -e "s|\${SECRET_KEY}|$secret_key|g" \
        -e "s|\${JWT_SECRET_KEY}|$jwt_secret|g" \
        -e "s|\${DB_PASSWORD}|$db_password|g" \
        -e "s|\${REDIS_PASSWORD}|$redis_password|g" \
        -e "s|\${UVICORN_WORKERS}|$uvicorn_workers|g" \
        -e "s|\$(date)|$(date)|g")
    
    # Write environment file
    echo "$env_content" > "$ENV_FILE"
    
    # Set secure permissions
    chmod 600 "$ENV_FILE"
    
    log_success "Environment configuration generated: $ENV_FILE"
    log_info "Generated secure values for secrets"
}

# Generate configuration files
generate_configuration_files() {
    log_step "Generating configuration files"
    
    # Create main configuration directory
    mkdir -p "$CONFIG_DIR"
    
    # Generate setup configuration
    cat > "$CONFIG_FILE" << EOF
# GOAT-PREDICTION Setup Configuration
# Generated: $(date)

setup:
  environment: $ENVIRONMENT
  mode: $SETUP_MODE
  platform: $OS_TYPE
  version: "2.0.0"
  timestamp: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

system:
  detected_os: "$OS_TYPE"
  os_version: "$OS_VERSION"
  hostname: "$HOSTNAME"
  username: "$USER_NAME"
  user_id: $USER_ID
  cpu_cores: $CPU_CORES
  total_memory_gb: $TOTAL_MEMORY
  available_disk: "$AVAILABLE_DISK"

paths:
  root: "$ROOT_DIR"
  config: "$CONFIG_DIR"
  secrets: "$SECRETS_DIR"
  logs: "$LOG_DIR"
  backups: "$BACKUP_DIR"
  virtualenv: "$ROOT_DIR/.venv"
  environment_file: "$ENV_FILE"

components:
  python: true
  nodejs: true
  database: true
  redis: true
  docker: $([[ "$SETUP_MODE" =~ ^(complete|custom)$ ]] && echo "true" || echo "false")
  kubernetes: false
  monitoring: true
  ml_models: $([[ "$SETUP_MODE" =~ ^(complete|custom)$ ]] && echo "true" || echo "false")

security:
  encryption_enabled: true
  certificates_generated: $GENERATE_CERTIFICATES
  secrets_protected: true
  firewall_configured: false

services:
  postgresql:
    enabled: true
    host: localhost
    port: 5432
  redis:
    enabled: true
    host: localhost
    port: 6379
  api_gateway:
    enabled: true
    port: 8000
  prediction_engine:
    enabled: true
    port: 8001
  frontend:
    enabled: true
    port: 3000
  monitoring:
    enabled: true
    prometheus_port: 9090
    grafana_port: 3000
EOF
    
    # Generate application configuration
    local app_config="$CONFIG_DIR/application.yaml"
    cat > "$app_config" << EOF
# GOAT-PREDICTION Application Configuration

app:
  name: "GOAT-PREDICTION"
  version: "2.0.0"
  environment: "$ENVIRONMENT"
  debug: $([ "$ENVIRONMENT" = "development" ] && echo "true" || echo "false")
  timezone: "UTC"

api:
  title: "GOAT-PREDICTION API"
  description: "Ultimate Sports Prediction Platform"
  version: "2.0.0"
  docs_url: "/docs"
  redoc_url: "/redoc"
  openapi_url: "/openapi.json"

server:
  host: "0.0.0.0"
  port: 8000
  workers: $((CPU_CORES * 2 + 1))
  reload: $([ "$ENVIRONMENT" = "development" ] && echo "true" || echo "false")
  access_log: true
  timeout: 60

database:
  postgresql:
    url: "\${DATABASE_URL}"
    pool_size: 20
    max_overflow: 40
    echo: $([ "$ENVIRONMENT" = "development" ] && echo "true" || echo "false")
    
  redis:
    url: "\${REDIS_URL}"
    decode_responses: true
    socket_keepalive: true

cache:
  default_ttl: 300
  max_size_mb: 1024
  backend: "redis"

logging:
  level: "$([ "$ENVIRONMENT" = "development" ] && echo "DEBUG" || echo "INFO")"
  format: "json"
  file: "./logs/app.log"
  rotation: "100 MB"
  retention: "30 days"

monitoring:
  enabled: true
  metrics_path: "/metrics"
  health_check_path: "/health"
  prometheus:
    enabled: true
    port: 9090
  grafana:
    enabled: true
    port: 3000

security:
  cors_origins:
    - "http://localhost:3000"
    - "http://localhost:8000"
  rate_limit:
    enabled: true
    requests: 100
    window: 60
  jwt:
    algorithm: "HS256"
    access_expire_minutes: 30
    refresh_expire_days: 7

features:
  predictions:
    enabled: true
    confidence_threshold: 0.6
    update_interval: 60
  betting:
    enabled: true
    min_stake: 1.0
    max_stake: 1000.0
    default_bankroll: 10000.0
  analytics:
    enabled: true
    retention_days: 365
EOF
    
    # Generate ML configuration for complete mode
    if [[ "$SETUP_MODE" =~ ^(complete|custom)$ ]]; then
        local ml_config="$CONFIG_DIR/ml_config.yaml"
        cat > "$ml_config" << EOF
# GOAT-PREDICTION Machine Learning Configuration

ml:
  environment: "$ENVIRONMENT"
  framework: "pytorch"  # pytorch, tensorflow, sklearn
  device: "auto"  # auto, cpu, cuda, mps
  precision: "float32"  # float32, float16, bfloat16
  
  training:
    batch_size: 32
    epochs: 100
    learning_rate: 0.001
    early_stopping_patience: 10
    validation_split: 0.2
    random_seed: 42
    
  inference:
    batch_size: 64
    workers: $CPU_CORES
    timeout: 30
    
  models:
    football:
      match_winner:
        type: "ensemble"
        version: "1.0.0"
        features: 128
      over_under:
        type: "regression"
        version: "1.0.0"
        features: 96
      exact_score:
        type: "classification"
        version: "1.0.0"
        features: 112
        
    basketball:
      moneyline:
        type: "gradient_boosting"
        version: "1.0.0"
        features: 85
      point_spread:
        type: "regression"
        version: "1.0.0"
        features: 92
        
    tennis:
      match_winner:
        type: "neural_network"
        version: "1.0.0"
        features: 76
        
  feature_store:
    type: "feast"
    registry: "./feature_store"
    host: "localhost"
    port: 6566
    
  experiment_tracking:
    enabled: true
    backend: "mlflow"  # mlflow, wandb, comet
    tracking_uri: "./mlruns"
    
  model_registry:
    enabled: true
    backend: "mlflow"
    registry_uri: "./models"
    
  hyperparameter_tuning:
    enabled: true
    backend: "optuna"
    n_trials: 100
    timeout: 3600
EOF
    fi
    
    # Generate Docker configuration
    local docker_config="$CONFIG_DIR/docker.yaml"
    cat > "$docker_config" << EOF
# GOAT-PREDICTION Docker Configuration

version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: "\${DB_NAME}"
      POSTGRES_USER: "\${DB_USER}"
      POSTGRES_PASSWORD: "\${DB_PASSWORD}"
    ports:
      - "\${DB_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
      
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass "\${REDIS_PASSWORD}"
    ports:
      - "\${REDIS_PORT}:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      
  api-gateway:
    build: ./backend/api-gateway
    environment:
      APP_ENV: "\${APP_ENV}"
      DATABASE_URL: "\${DATABASE_URL}"
      REDIS_URL: "\${REDIS_URL}"
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      
  prediction-engine:
    build: ./backend/prediction-engine
    environment:
      APP_ENV: "\${APP_ENV}"
      DATABASE_URL: "\${DATABASE_URL}"
      REDIS_URL: "\${REDIS_URL}"
      ML_MODEL_DIR: "/app/models"
    ports:
      - "8001:8001"
    depends_on:
      - api-gateway
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
      
  frontend:
    build: ./frontend/web-app
    environment:
      NEXT_PUBLIC_API_URL: "http://localhost:8000"
      NEXT_PUBLIC_ENV: "\${APP_ENV}"
    ports:
      - "3000:3000"
    depends_on:
      - api-gateway
      
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
      
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "\${GRAFANA_PASSWORD}"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
EOF
    
    log_success "Configuration files generated in: $CONFIG_DIR"
}

# Generate SSL certificates
generate_ssl_certificates() {
    if [ "$GENERATE_CERTIFICATES" != "true" ]; then
        log_info "Skipping SSL certificate generation"
        return 0
    fi
    
    log_step "Generating SSL certificates"
    
    local ssl_dir="$CONFIG_DIR/ssl"
    mkdir -p "$ssl_dir"
    
    # Generate self-signed certificate for development
    if [ "$ENVIRONMENT" = "development" ] || [ "$ENVIRONMENT" = "staging" ]; then
        log_info "Generating self-signed SSL certificate for $ENVIRONMENT..."
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$ssl_dir/server.key" \
            -out "$ssl_dir/server.crt" \
            -subj "/C=US/ST=State/L=City/O=GOAT-PREDICTION/CN=localhost" \
            >> "$SETUP_LOG" 2>> "$ERROR_LOG"
        
        if [ $? -eq 0 ]; then
            chmod 600 "$ssl_dir/server.key"
            log_success "Self-signed SSL certificate generated: $ssl_dir/server.crt"
        else
            log_warning "Failed to generate self-signed certificate"
        fi
    fi
    
    # For production, provide instructions
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "Production environment detected"
        log_info "For production SSL certificates, please:"
        log_info "1. Use Let's Encrypt with certbot"
        log_info "2. Purchase certificates from a trusted CA"
        log_info "3. Place certificates in: $ssl_dir/"
        log_info "   - server.crt (certificate)"
        log_info "   - server.key (private key)"
        log_info "   - ca.crt (CA bundle, if needed)"
    fi
    
    # Generate SSL configuration for nginx
    local nginx_ssl_conf="$CONFIG_DIR/nginx/ssl.conf"
    mkdir -p "$(dirname "$nginx_ssl_conf")"
    
    cat > "$nginx_ssl_conf" << EOF
# SSL Configuration for GOAT-PREDICTION

ssl_certificate $ssl_dir/server.crt;
ssl_certificate_key $ssl_dir/server.key;

# SSL Protocols
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;

# SSL Ciphers
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;

# SSL Session
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# SSL Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Security Headers
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
EOF
    
    log_success "SSL configuration completed"
}

# Setup security
setup_security() {
    if [ "$SETUP_SECURITY" != "true" ]; then
        log_info "Skipping security setup"
        return 0
    fi
    
    log_step "Setting up security"
    
    # Create secrets directory with secure permissions
    mkdir -p "$SECRETS_DIR"
    chmod 700 "$SECRETS_DIR"
    
    # Generate random secrets if not exists
    local secrets=(
        "jwt_secret.key"
        "api_keys.env"
        "database_passwords.env"
        "encryption_key.key"
    )
    
    for secret in "${secrets[@]}"; do
        local secret_file="$SECRETS_DIR/$secret"
        
        if [ ! -f "$secret_file" ] || [ "$FORCE_RECONFIGURE" = "true" ]; then
            case "$secret" in
                *.key)
                    # Generate random key
                    openssl rand -base64 32 > "$secret_file" 2>/dev/null || \
                        echo "dev-$(date +%s)-$(openssl rand -hex 16 2>/dev/null || echo "random")" > "$secret_file"
                    chmod 600 "$secret_file"
                    log_info "Generated secret key: $secret"
                    ;;
                    
                *.env)
                    # Create empty environment file
                    echo "# Secret: $secret" > "$secret_file"
                    echo "# Generated: $(date)" >> "$secret_file"
                    echo "" >> "$secret_file"
                    chmod 600 "$secret_file"
                    log_info "Created secret file: $secret"
                    ;;
            esac
        fi
    done
    
    # Create .gitignore for secrets directory
    local gitignore_file="$SECRETS_DIR/.gitignore"
    cat > "$gitignore_file" << EOF
# DO NOT COMMIT SECRETS TO VERSION CONTROL
*
!.gitignore
EOF
    
    # Setup firewall rules (Linux only)
    if [ "$OS_TYPE" = "linux" ] && command -v ufw &> /dev/null; then
        log_info "Configuring firewall (UFW)..."
        
        # Allow SSH
        sudo ufw allow 22/tcp 2>> "$ERROR_LOG" || true
        
        # Allow application ports
        sudo ufw allow 8000/tcp 2>> "$ERROR_LOG" || true  # API Gateway
        sudo ufw allow 3000/tcp 2>> "$ERROR_LOG" || true  # Frontend
        sudo ufw allow 5432/tcp 2>> "$ERROR_LOG" || true  # PostgreSQL
        sudo ufw allow 6379/tcp 2>> "$ERROR_LOG" || true  # Redis
        
        # Enable firewall
        sudo ufw --force enable 2>> "$ERROR_LOG" || true
        
        log_info "Firewall configured (if UFW was available)"
    fi
    
    # Create security audit script
    local audit_script="$SECRETS_DIR/security_audit.sh"
    cat > "$audit_script" << 'EOF'
#!/bin/bash
# GOAT-PREDICTION Security Audit Script

echo "🔒 Security Audit Report"
echo "========================"
echo "Generated: $(date)"
echo ""

# Check file permissions
echo "1. File Permissions Check:"
find . -name "*.key" -o -name "*.pem" -o -name "*.crt" 2>/dev/null | while read -r file; do
    perms=$(stat -c "%a %n" "$file" 2>/dev/null || stat -f "%p %N" "$file" 2>/dev/null)
    if [[ ! "$perms" =~ ^600 ]]; then
        echo "   WARNING: $file has permissions $perms (should be 600)"
    fi
done
echo ""

# Check for exposed secrets
echo "2. Potential Secret Exposure:"
if grep -r "password\|secret\|key\|token" --include="*.py" --include="*.js" --include="*.json" . 2>/dev/null | \
   grep -v "test\|example\|dummy\|placeholder" | grep -v ".venv" | head -10; then
    echo "   WARNING: Potential secrets found in code"
fi
echo ""

# Check environment files
echo "3. Environment Files:"
if [ -f ".env.production" ]; then
    if grep -q "dev\|test\|example" ".env.production"; then
        echo "   WARNING: .env.production may contain development values"
    fi
fi
echo ""

echo "✅ Audit completed"
EOF
    
    chmod 700 "$audit_script"
    
    log_success "Security setup completed"
}

# Initialize database
initialize_database() {
    if [ "$INITIALIZE_DATABASE" != "true" ]; then
        log_info "Skipping database initialization"
        return 0
    fi
    
    log_step "Initializing database"
    
    # Check if PostgreSQL is available
    if ! command -v psql &> /dev/null; then
        log_warning "PostgreSQL client not found. Skipping database initialization."
        return 0
    fi
    
    # Load environment variables
    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE"
        set +a
    fi
    
    # Check database connection
    log_info "Testing database connection..."
    
    if [ -z "${DATABASE_URL:-}" ]; then
        log_warning "DATABASE_URL not set. Skipping database initialization."
        return 0
    fi
    
    # Extract connection details
    local dbname=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/.*\/\([^?]*\).*/\1/p')
    local host=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:/]*\).*/\1/p')
    local port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\).*/\1/p')
    local user=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    local password=$(echo "$DATABASE_URL" | sed -n 's/.*:\([^@]*\)@.*/\1/p')
    
    # Try to connect to PostgreSQL
    export PGPASSWORD="$password"
    
    if ! psql -h "$host" -p "${port:-5432}" -U "$user" -d "postgres" -c "SELECT 1;" -t 2>/dev/null; then
        log_warning "Cannot connect to PostgreSQL. Skipping database initialization."
        log_info "Please ensure PostgreSQL is running and credentials are correct."
        unset PGPASSWORD
        return 0
    fi
    
    # Check if database exists
    if psql -h "$host" -p "${port:-5432}" -U "$user" -d "$dbname" -c "SELECT 1;" -t 2>/dev/null; then
        log_info "Database '$dbname' already exists"
        
        if [ "$FORCE_RECONFIGURE" = "true" ]; then
            log_warning "Force reconfiguration: Dropping and recreating database..."
            psql -h "$host" -p "${port:-5432}" -U "$user" -d "postgres" \
                -c "DROP DATABASE IF EXISTS $dbname;" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
            psql -h "$host" -p "${port:-5432}" -U "$user" -d "postgres" \
                -c "CREATE DATABASE $dbname;" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
        else
            unset PGPASSWORD
            return 0
        fi
    else
        # Create database
        log_info "Creating database '$dbname'..."
        psql -h "$host" -p "${port:-5432}" -U "$user" -d "postgres" \
            -c "CREATE DATABASE $dbname;" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    fi
    
    # Run database migrations if Alembic is available
    local alembic_dir="$ROOT_DIR/backend/api-gateway"
    
    if [ -f "$alembic_dir/alembic.ini" ]; then
        log_info "Running database migrations..."
        
        cd "$alembic_dir"
        
        # Create migrations if needed
        if [ ! -d "$alembic_dir/migrations" ]; then
            log_info "Initializing Alembic..."
            alembic init migrations >> "$SETUP_LOG" 2>> "$ERROR_LOG"
            
            # Update alembic.ini with database URL
            sed -i "s|sqlalchemy.url = .*|sqlalchemy.url = $DATABASE_URL|" "$alembic_dir/alembic.ini"
        fi
        
        # Run migrations
        alembic upgrade head >> "$SETUP_LOG" 2>> "$ERROR_LOG"
        
        cd - > /dev/null
    else
        # Create basic schema if no migrations
        log_info "Creating basic database schema..."
        
        cat > "$TEMP_DIR/init_schema.sql" << EOF
-- GOAT-PREDICTION Database Schema
-- Generated: $(date)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Sports table
CREATE TABLE IF NOT EXISTS sports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    code VARCHAR(10) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country_code VARCHAR(3),
    sport_id INTEGER REFERENCES sports(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, sport_id)
);

-- Matches table
CREATE TABLE IF NOT EXISTS matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100),
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    sport_id INTEGER REFERENCES sports(id),
    match_date TIMESTAMP NOT NULL,
    league VARCHAR(255),
    status VARCHAR(50) DEFAULT 'scheduled',
    home_score INTEGER,
    away_score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id),
    model_version VARCHAR(50) NOT NULL,
    home_win_probability DECIMAL(5,4),
    away_win_probability DECIMAL(5,4),
    draw_probability DECIMAL(5,4),
    recommended_bet VARCHAR(50),
    confidence DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(match_id, model_version)
);

-- Bets table
CREATE TABLE IF NOT EXISTS bets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    prediction_id UUID REFERENCES predictions(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    outcome VARCHAR(50), -- 'win', 'lose', 'pending'
    profit_loss DECIMAL(10,2),
    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settled_at TIMESTAMP
);

-- Model performance table
CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    sport_id INTEGER REFERENCES sports(id),
    accuracy DECIMAL(5,4),
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    roi DECIMAL(6,4),
    sample_size INTEGER,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_name, sport_id, evaluated_at)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_matches_sport_date ON matches(sport_id, match_date);
CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_bets_user_id ON bets(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS \$\$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
\$\$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data
INSERT INTO sports (name, code) VALUES
    ('Football', 'FOOT'),
    ('Basketball', 'BASK'),
    ('Tennis', 'TENN'),
    ('Baseball', 'BASE'),
    ('Esports', 'ESPT')
ON CONFLICT (code) DO NOTHING;

-- Create admin user (password: admin123 - CHANGE IN PRODUCTION)
INSERT INTO users (email, username, password_hash, full_name, is_admin) VALUES
    ('admin@goat-prediction.com', 'admin', '\$2b\$12\$YourHashedPasswordHere', 'System Administrator', TRUE)
ON CONFLICT (email) DO NOTHING;
EOF
        
        # Execute schema
        psql -h "$host" -p "${port:-5432}" -U "$user" -d "$dbname" \
            -f "$TEMP_DIR/init_schema.sql" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    fi
    
    unset PGPASSWORD
    
    log_success "Database initialization completed"
}

# Setup Docker services
setup_docker_services() {
    if [[ ! "$SETUP_MODE" =~ ^(complete|custom)$ ]] || [[ "$OS_TYPE" =~ ^(docker|kubernetes)$ ]]; then
        log_info "Skipping Docker services setup"
        return 0
    fi
    
    log_step "Setting up Docker services"
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not found. Skipping Docker services setup."
        return 0
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_warning "Docker Compose not found. Skipping Docker services setup."
        return 0
    fi
    
    # Create Docker Compose file
    local docker_compose_file="$ROOT_DIR/docker-compose.$ENVIRONMENT.yml"
    
    if [ ! -f "$docker_compose_file" ] || [ "$FORCE_RECONFIGURE" = "true" ]; then
        log_info "Creating Docker Compose configuration..."
        
        cat > "$docker_compose_file" << EOF
version: '3.8'

services:
  # Database
  postgres:
    image: postgres:15-alpine
    container_name: goat-postgres-\${ENVIRONMENT}
    environment:
      POSTGRES_DB: \${DB_NAME}
      POSTGRES_USER: \${DB_USER}
      POSTGRES_PASSWORD: \${DB_PASSWORD}
    ports:
      - "\${DB_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - goat-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis
  redis:
    image: redis:7-alpine
    container_name: goat-redis-\${ENVIRONMENT}
    command: redis-server --requirepass "\${REDIS_PASSWORD}"
    ports:
      - "\${REDIS_PORT}:6379"
    volumes:
      - redis_data:/data
    networks:
      - goat-network
    healthcheck:
      test: ["CMD", "redis-cli", "--auth", "\${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # API Gateway
  api-gateway:
    build:
      context: ./backend/api-gateway
      dockerfile: Dockerfile
    container_name: goat-api-\${ENVIRONMENT}
    environment:
      APP_ENV: \${APP_ENV}
      DATABASE_URL: \${DATABASE_URL}
      REDIS_URL: \${REDIS_URL}
      SECRET_KEY: \${SECRET_KEY}
      JWT_SECRET_KEY: \${JWT_SECRET_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models
    networks:
      - goat-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  # Prediction Engine
  prediction-engine:
    build:
      context: ./backend/prediction-engine
      dockerfile: Dockerfile
    container_name: goat-prediction-\${ENVIRONMENT}
    environment:
      APP_ENV: \${APP_ENV}
      DATABASE_URL: \${DATABASE_URL}
      REDIS_URL: \${REDIS_URL}
      ML_MODEL_DIR: "/app/models"
    ports:
      - "8001:8001"
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
      - ./data:/app/data
    networks:
      - goat-network
    depends_on:
      - api-gateway
    restart: unless-stopped

  # Frontend
  frontend:
    build:
      context: ./frontend/web-app
      dockerfile: Dockerfile
    container_name: goat-frontend-\${ENVIRONMENT}
    environment:
      NEXT_PUBLIC_API_URL: "http://localhost:8000"
      NEXT_PUBLIC_ENV: \${APP_ENV}
    ports:
      - "3000:3000"
    networks:
      - goat-network
    depends_on:
      - api-gateway
    restart: unless-stopped

  # Monitoring - Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: goat-prometheus-\${ENVIRONMENT}
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - goat-network
    restart: unless-stopped

  # Monitoring - Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: goat-grafana-\${ENVIRONMENT}
    environment:
      GF_SECURITY_ADMIN_PASSWORD: \${GRAFANA_PASSWORD:-admin}
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/datasources:/etc/grafana/provisioning/datasources
    networks:
      - goat-network
    depends_on:
      - prometheus
    restart: unless-stopped

  # Message Queue (RabbitMQ)
  rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: goat-rabbitmq-\${ENVIRONMENT}
    environment:
      RABBITMQ_DEFAULT_USER: \${RABBITMQ_USER:-guest}
      RABBITMQ_DEFAULT_PASS: \${RABBITMQ_PASSWORD:-guest}
    ports:
      - "5672:5672"   # AMQP
      - "15672:15672" # Management UI
    networks:
      - goat-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  goat-network:
    driver: bridge
    name: goat-network-\${ENVIRONMENT}
EOF
        
        log_success "Docker Compose configuration created: $docker_compose_file"
    fi
    
    # Build Docker images
    log_info "Building Docker images..."
    
    cd "$ROOT_DIR"
    
    # Build API Gateway
    if [ -f "$ROOT_DIR/backend/api-gateway/Dockerfile" ]; then
        log_info "Building API Gateway image..."
        docker build -t goat-api-gateway:$ENVIRONMENT \
            -f "$ROOT_DIR/backend/api-gateway/Dockerfile" \
            "$ROOT_DIR/backend/api-gateway" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    fi
    
    # Build Prediction Engine
    if [ -f "$ROOT_DIR/backend/prediction-engine/Dockerfile" ]; then
        log_info "Building Prediction Engine image..."
        docker build -t goat-prediction-engine:$ENVIRONMENT \
            -f "$ROOT_DIR/backend/prediction-engine/Dockerfile" \
            "$ROOT_DIR/backend/prediction-engine" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    fi
    
    # Build Frontend
    if [ -f "$ROOT_DIR/frontend/web-app/Dockerfile" ]; then
        log_info "Building Frontend image..."
        docker build -t goat-frontend:$ENVIRONMENT \
            -f "$ROOT_DIR/frontend/web-app/Dockerfile" \
            "$ROOT_DIR/frontend/web-app" >> "$SETUP_LOG" 2>> "$ERROR_LOG"
    fi
    
    cd - > /dev/null
    
    log_success "Docker services setup completed"
}

# Validate setup
validate_setup() {
    if [ "$VALIDATE_SETUP" != "true" ]; then
        log_info "Skipping setup validation"
        return 0
    fi
    
    log_step "Validating setup"
    
    local validation_errors=0
    local validation_warnings=0
    
    # Check Python environment
    log_info "Validating Python environment..."
    if [ -d "$ROOT_DIR/.venv" ]; then
        if source "$ROOT_DIR/.venv/bin/activate" && python3 -c "import sys; print(f'Python {sys.version}')" >> "$SETUP_LOG" 2>> "$ERROR_LOG"; then
            log_success "Python virtual environment is active"
        else
            log_error "Python virtual environment validation failed"
            validation_errors=$((validation_errors + 1))
        fi
    else
        log_warning "Python virtual environment not found"
        validation_warnings=$((validation_warnings + 1))
    fi
    
    # Check environment file
    log_info "Validating environment configuration..."
    if [ -f "$ENV_FILE" ]; then
        # Check for placeholder values
        if grep -q "your-\|example\|change-this\|placeholder" "$ENV_FILE"; then
            log_warning "Environment file contains placeholder values"
            validation_warnings=$((validation_warnings + 1))
        else
            log_success "Environment file looks properly configured"
        fi
    else
        log_error "Environment file not found: $ENV_FILE"
        validation_errors=$((validation_errors + 1))
    fi
    
    # Check configuration files
    log_info "Validating configuration files..."
    local required_configs=(
        "$CONFIG_FILE"
        "$CONFIG_DIR/application.yaml"
    )
    
    for config in "${required_configs[@]}"; do
        if [ -f "$config" ]; then
            log_success "Configuration file exists: $(basename "$config")"
        else
            log_error "Missing configuration file: $(basename "$config")"
            validation_errors=$((validation_errors + 1))
        fi
    done
    
    # Check directory permissions
    log_info "Validating directory permissions..."
    local secure_dirs=(
        "$SECRETS_DIR"
    )
    
    for dir in "${secure_dirs[@]}"; do
        if [ -d "$dir" ]; then
            local perms=$(stat -c "%a" "$dir" 2>/dev/null || stat -f "%p" "$dir" 2>/dev/null)
            if [[ "$perms" =~ ^700 ]]; then
                log_success "Secure permissions on: $dir"
            else
                log_warning "Insecure permissions on $dir: $perms (should be 700)"
                validation_warnings=$((validation_warnings + 1))
            fi
        fi
    done
    
    # Test service connections
    log_info "Testing service connections..."
    
    # Load environment variables for testing
    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE"
        set +a
    fi
    
    # Test PostgreSQL if configured
    if [ -n "${DATABASE_URL:-}" ]; then
        log_info "Testing PostgreSQL connection..."
        export PGPASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\([^@]*\)@.*/\1/p')
        
        local dbname=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/.*\/\([^?]*\).*/\1/p')
        local host=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:/]*\).*/\1/p')
        local port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\).*/\1/p')
        local user=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
        
        if psql -h "$host" -p "${port:-5432}" -U "$user" -d "$dbname" -c "SELECT 1;" -t 2>/dev/null; then
            log_success "PostgreSQL connection successful"
        else
            log_warning "PostgreSQL connection failed (service may not be running)"
            validation_warnings=$((validation_warnings + 1))
        fi
        
        unset PGPASSWORD
    fi
    
    # Generate validation report
    local validation_report="$LOG_DIR/validation_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$validation_report" << EOF
GOAT-PREDICTION Setup Validation Report
========================================
Generated: $(date)
Environment: $ENVIRONMENT
Setup Mode: $SETUP_MODE
Platform: $OS_TYPE

SUMMARY:
  Errors: $validation_errors
  Warnings: $validation_warnings
  Status: $(if [ $validation_errors -eq 0 ]; then echo "PASSED"; else echo "FAILED"; fi)

DETAILS:
$(if [ $validation_errors -gt 0 ] || [ $validation_warnings -gt 0 ]; then
    tail -20 "$SETUP_LOG" | grep -E "(ERROR|WARNING)" | sed 's/^/  /'
else
    echo "  No issues detected"
fi)

RECOMMENDATIONS:
$(if [ $validation_errors -gt 0 ]; then
    echo "  ❌ Fix errors before proceeding"
fi
if [ $validation_warnings -gt 0 ]; then
    echo "  ⚠️  Review warnings and address if needed"
fi
if [ $validation_errors -eq 0 ] && [ $validation_warnings -eq 0 ]; then
    echo "  ✅ Setup is ready for use"
fi)

NEXT STEPS:
  1. Review the setup logs: $SETUP_LOG
  2. Check configuration files in: $CONFIG_DIR
  3. Secure your secrets in: $SECRETS_DIR
  4. Start services with: make start-$ENVIRONMENT
  5. Access the application at: http://localhost:3000

EOF
    
    if [ $validation_errors -eq 0 ]; then
        log_success "✅ Setup validation PASSED with $validation_warnings warnings"
        log_info "Validation report: $validation_report"
        return 0
    else
        log_error "❌ Setup validation FAILED with $validation_errors errors and $validation_warnings warnings"
        log_info "Validation report: $validation_report"
        return 1
    fi
}

# Create setup summary
create_setup_summary() {
    log_step "Creating setup summary"
    
    local summary_file="$LOG_DIR/setup_summary_$(date +%Y%m%d_%H%M%S).md"
    local duration=$(( $(date +%s) - START_TIME ))
    
    cat > "$summary_file" << EOF
# 🐐 GOAT-PREDICTION Setup Summary

## Overview
- **Environment**: $ENVIRONMENT
- **Setup Mode**: $SETUP_MODE
- **Platform**: $OS_TYPE ($OS_VERSION)
- **Duration**: ${duration} seconds
- **Status**: COMPLETED ✅

## System Information
- **Hostname**: $HOSTNAME
- **Username**: $USER_NAME
- **CPU Cores**: $CPU_CORES
- **Memory**: ${TOTAL_MEMORY}GB
- **Available Disk**: $AVAILABLE_DISK

## Components Installed

### System Dependencies
- Python $(python3 --version 2>/dev/null || echo "Not installed")
- Node.js $(node --version 2>/dev/null || echo "Not installed")
- Docker $(docker --version 2>/dev/null | cut -d' ' -f3 | sed 's/,//' || echo "Not installed")
- PostgreSQL Client $(psql --version 2>/dev/null | cut -d' ' -f3 || echo "Not installed")
- Redis Tools $(redis-cli --version 2>/dev/null | cut -d' ' -f2 || echo "Not installed")

### Python Packages
Virtual environment created at: \`$ROOT_DIR/.venv\`

Key packages installed:
$(if [ -d "$ROOT_DIR/.venv" ]; then
    source "$ROOT_DIR/.venv/bin/activate"
    pip list 2>/dev/null | grep -E "(fastapi|pydantic|sqlalchemy|pandas|numpy|torch|tensorflow|scikit)" | head -10 | sed 's/^/- /'
fi)

### Configuration Files
- Environment: \`$ENV_FILE\`
- Application Config: \`$CONFIG_DIR/application.yaml\`
- Docker Compose: \`$ROOT_DIR/docker-compose.$ENVIRONMENT.yml\`
- ML Config: \`$CONFIG_DIR/ml_config.yaml\` $(if [[ "$SETUP_MODE" =~ ^(complete|custom)$ ]]; then echo "✅"; else echo "⏭️"; fi)

### Security
- Secrets Directory: \`$SECRETS_DIR\` (permissions: 700)
- SSL Certificates: $(if [ -f "$CONFIG_DIR/ssl/server.crt" ]; then echo "✅ Generated"; else echo "⏭️ Not generated"; fi)
- Environment File: $(if [ -f "$ENV_FILE" ]; then echo "✅ Generated (permissions: 600)"; else echo "❌ Missing"; fi)

## Services Configured

### Database
- **PostgreSQL**: \`${DB_HOST:-localhost}:${DB_PORT:-5432}/${DB_NAME:-goat_prediction_$ENVIRONMENT}\`
- **Redis**: \`${REDIS_HOST:-localhost}:${REDIS_PORT:-6379}/${REDIS_DB:-0}\`

### Application Services
- **API Gateway**: http://localhost:8000
- **Prediction Engine**: http://localhost:8001
- **Frontend**: http://localhost:3000
- **Monitoring**: http://localhost:9090 (Prometheus), http://localhost:3001 (Grafana)

## Next Steps

### 1. Start Services
\`\`\`bash
# Development
make start-dev

# Production
make start-prod

# Using Docker Compose
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d
\`\`\`

### 2. Verify Installation
\`\`\`bash
# Check service health
curl http://localhost:8000/health

# Check database connection
psql "\$DATABASE_URL" -c "SELECT 1;"

# Run tests
make test
\`\`\`

### 3. Access Applications
- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Monitoring Dashboard**: http://localhost:3001 (admin/\${GRAFANA_PASSWORD:-admin})

### 4. Security Checklist
- [ ] Change default passwords in \`$ENV_FILE\`
- [ ] Configure SSL certificates for production
- [ ] Set up firewall rules
- [ ] Configure backup strategy
- [ ] Set up monitoring alerts

### 5. Development
\`\`\`bash
# Activate virtual environment
source .venv/bin/activate

# Install additional packages
pip install -r requirements-dev.txt

# Run development server
make dev
\`\`\`

## Troubleshooting

### Common Issues
1. **Port conflicts**: Check if ports 3000, 8000, 5432, 6379 are free
2. **Database connection**: Ensure PostgreSQL is running
3. **Permission errors**: Check file permissions in \`$SECRETS_DIR\`
4. **Missing dependencies**: Run \`$0 --force\` to reinstall

### Logs
- Setup Log: \`$SETUP_LOG\`
- Error Log: \`$ERROR_LOG\`
- Application Logs: \`$ROOT_DIR/logs/\`

## Support
- Documentation: \`docs/\` directory
- Issues: GitHub repository
- Community: Discord/Slack channel

---

*Setup completed on $(date)*  
*GOAT-PREDICTION v2.0.0*
EOF
    
    log_success "Setup summary created: $summary_file"
    
    # Display quick start instructions
    log_header "🚀 QUICK START"
    echo "To start GOAT-PREDICTION, run:"
    echo ""
    echo "  cd $ROOT_DIR"
    echo "  source .venv/bin/activate"
    echo "  make start-$ENVIRONMENT"
    echo ""
    echo "Or using Docker:"
    echo ""
    echo "  docker-compose -f docker-compose.$ENVIRONMENT.yml up -d"
    echo ""
    echo "Access the application at: http://localhost:3000"
    echo "API Documentation: http://localhost:8000/docs"
    echo ""
    echo "📋 Full setup summary: $summary_file"
}

# Cleanup temporary files
cleanup_temp_files() {
    log_step "Cleaning up temporary files"
    
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        log_success "Temporary files cleaned up"
    fi
    
    # Cleanup old setup logs (keep 7 days)
    find "$LOG_DIR" -name "setup_*.log" -mtime +7 -delete 2>/dev/null || true
    find "$LOG_DIR" -name "errors_*.log" -mtime +7 -delete 2>/dev/null || true
}

# Main setup function
setup_environment() {
    log_step "Starting GOAT-PREDICTION Environment Setup"
    
    # Record start time
    START_TIME=$(date +%s)
    
    # Execute setup steps
    local steps=(
        "check_prerequisites"
        "detect_platform"
        "check_lock"
        "create_directory_structure"
        "backup_existing_config"
        "install_system_dependencies"
        "setup_python_environment"
        "setup_node_environment"
        "generate_environment_config"
        "generate_configuration_files"
        "generate_ssl_certificates"
        "setup_security"
        "initialize_database"
        "setup_docker_services"
        "validate_setup"
        "create_setup_summary"
        "cleanup_temp_files"
    )
    
    local failed_step=""
    local success_steps=0
    local total_steps=${#steps[@]}
    
    for step in "${steps[@]}"; do
        log_info "Executing step: $step"
        
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
    
    # Final status
    if [ -z "$failed_step" ]; then
        log_success "🎉 Environment setup completed successfully in ${DURATION} seconds!"
        log_success "📊 Success rate: $success_steps/$total_steps steps"
        log_success "🐐 GOAT-PREDICTION is ready for $ENVIRONMENT environment!"
        return 0
    else
        log_error "💥 Setup failed at step: $failed_step"
        log_error "📊 Success rate: $success_steps/$total_steps steps"
        log_error "⚠️  Check logs for details: $ERROR_LOG"
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
            -m|--mode)
                SETUP_MODE="$2"
                shift 2
                ;;
            -p|--platform)
                PLATFORM="$2"
                shift 2
                ;;
            -y|--yes)
                SKIP_CONFIRMATION="true"
                shift
                ;;
            --force)
                FORCE_RECONFIGURE="true"
                shift
                ;;
            --no-deps)
                INSTALL_DEPENDENCIES="false"
                shift
                ;;
            --no-security)
                SETUP_SECURITY="false"
                shift
                ;;
            --no-ssl)
                GENERATE_CERTIFICATES="false"
                shift
                ;;
            --no-db)
                INITIALIZE_DATABASE="false"
                shift
                ;;
            --no-validate)
                VALIDATE_SETUP="false"
                shift
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
    mkdir -p "$(dirname "$SETUP_LOG")"
    exec > >(tee -a "$SETUP_LOG")
    exec 2> >(tee -a "$ERROR_LOG")
    
    # Show banner
    show_banner
    
    # Confirm setup if not skipped
    if [ "$SKIP_CONFIRMATION" != "true" ]; then
        echo ""
        echo "Environment: $ENVIRONMENT"
        echo "Setup Mode: $SETUP_MODE"
        echo "Platform: $PLATFORM"
        echo ""
        read -p "Continue with setup? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Setup cancelled by user"
            exit 0
        fi
    fi
    
    # Run setup
    if setup_environment; then
        exit 0
    else
        exit 1
    fi
}

show_help() {
    cat << EOF
GOAT-PREDICTION Ultimate Environment Setup Script

Usage: $0 [OPTIONS]

Options:
  -e, --environment ENV    Target environment (development, staging, production)
  -m, --mode MODE         Setup mode: minimal, standard, complete, custom
  -p, --platform PLATFORM Target platform: auto, linux, macos, windows, docker
  -y, --yes               Skip confirmation prompts
  --force                 Force reconfiguration (overwrites existing config)
  --no-deps               Skip system dependencies installation
  --no-security           Skip security setup
  --no-ssl                Skip SSL certificate generation
  --no-db                 Skip database initialization
  --no-validate           Skip setup validation
  --help                  Show this help message

Examples:
  $0 --environment development --mode complete
  $0 --environment production --mode standard --yes
  $0 --environment staging --platform docker --no-db

Setup Modes:
  minimal    - Basic Python environment only
  standard   - Python + Node.js + basic services
  complete   - Full stack with ML dependencies and Docker
  custom     - Custom configuration (uses existing settings)

Environment Files:
  The script generates .env.{environment} files with appropriate
  configuration for each environment.

Output:
  - Environment configuration in .env.{environment}
  - Configuration files in .config/
  - Secure secrets in .secrets/
  - Setup logs in .logs/setup/
  - Backup of existing config in .backups/setup/

Requirements:
  - bash 4.0+
  - Internet connection for downloading dependencies
  - sudo privileges for system package installation (optional)

EOF
}

# =============================================================================
# EXECUTE
# =============================================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
