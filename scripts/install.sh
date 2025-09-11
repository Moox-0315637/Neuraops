#!/bin/bash

# =========================================================================
# NeuraOps Installation Script
# Complete installation of NeuraOps platform and dependencies
# =========================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Installation options
INSTALL_UV="${INSTALL_UV:-true}"
INSTALL_OLLAMA="${INSTALL_OLLAMA:-false}"
INSTALL_DOCKER="${INSTALL_DOCKER:-false}"
SETUP_ENV="${SETUP_ENV:-true}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         NeuraOps Platform Installation Script         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print step
print_step() {
    echo -e "${YELLOW}▸ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if [ -f /etc/debian_version ]; then
            DISTRO="debian"
        elif [ -f /etc/redhat-release ]; then
            DISTRO="redhat"
        else
            DISTRO="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
    
    print_info "Detected OS: $OS"
}

# Check Python version
check_python() {
    print_step "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d" " -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            print_success "Python $PYTHON_VERSION found"
        else
            print_error "Python 3.11+ required, but $PYTHON_VERSION found"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi
}

# Check Node.js
check_nodejs() {
    print_step "Checking Node.js installation..."
    
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version | cut -d"v" -f2)
        NODE_MAJOR=$(echo $NODE_VERSION | cut -d. -f1)
        
        if [ "$NODE_MAJOR" -ge 18 ]; then
            print_success "Node.js v$NODE_VERSION found"
        else
            print_error "Node.js 18+ required, but v$NODE_VERSION found"
            exit 1
        fi
    else
        print_error "Node.js not found. Please install Node.js 18+"
        exit 1
    fi
}

# Install UV package manager
install_uv() {
    if [[ "$INSTALL_UV" == "true" ]]; then
        print_step "Installing UV package manager..."
        
        if command -v uv &> /dev/null; then
            print_success "UV already installed"
        else
            curl -LsSf https://astral.sh/uv/install.sh | sh
            
            # Add to PATH
            export PATH="$HOME/.cargo/bin:$PATH"
            
            if command -v uv &> /dev/null; then
                print_success "UV installed successfully"
            else
                print_error "UV installation failed"
                exit 1
            fi
        fi
    fi
}

# Install Ollama
install_ollama() {
    if [[ "$INSTALL_OLLAMA" == "true" ]]; then
        print_step "Installing Ollama..."
        
        if command -v ollama &> /dev/null; then
            print_success "Ollama already installed"
        else
            if [[ "$OS" == "macos" ]]; then
                print_info "Please download Ollama from https://ollama.com/download"
            elif [[ "$OS" == "linux" ]]; then
                curl -fsSL https://ollama.com/install.sh | sh
            fi
            
            if command -v ollama &> /dev/null; then
                print_success "Ollama installed successfully"
                
                # Pull gpt-oss model
                print_step "Pulling gpt-oss:20b model..."
                ollama pull gpt-oss:20b
                print_success "Model downloaded"
            else
                print_error "Ollama installation failed"
            fi
        fi
    fi
}

# Setup Python environment
setup_python_env() {
    print_step "Setting up Python environments..."
    
    # Setup Core
    cd "$PROJECT_ROOT/neuraops-core"
    if command -v uv &> /dev/null; then
        print_step "Installing Core dependencies with UV..."
        uv sync
        print_success "Core dependencies installed"
    else
        print_step "Creating Core virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -e .
        deactivate
        print_success "Core environment created"
    fi
    
    # Setup Agent
    cd "$PROJECT_ROOT/neuraops-agent"
    if command -v uv &> /dev/null; then
        print_step "Installing Agent dependencies with UV..."
        uv sync
        print_success "Agent dependencies installed"
    else
        print_step "Creating Agent virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -e .
        deactivate
        print_success "Agent environment created"
    fi
}

# Setup Node.js environment
setup_nodejs_env() {
    print_step "Setting up Node.js environment..."
    
    cd "$PROJECT_ROOT/neuraops-ui"
    
    # Check for pnpm
    if command -v pnpm &> /dev/null; then
        print_step "Installing UI dependencies with pnpm..."
        pnpm install
    else
        print_step "Installing UI dependencies with npm..."
        npm install
    fi
    
    print_success "UI dependencies installed"
}

# Setup environment files
setup_env_files() {
    if [[ "$SETUP_ENV" == "true" ]]; then
        print_step "Setting up environment files..."
        
        # Core .env
        if [ ! -f "$PROJECT_ROOT/neuraops-core/.env" ]; then
            cp "$PROJECT_ROOT/neuraops-core/.env.example" "$PROJECT_ROOT/neuraops-core/.env" 2>/dev/null || true
            print_info "Created neuraops-core/.env - Please configure it"
        fi
        
        # Agent .env
        if [ ! -f "$PROJECT_ROOT/neuraops-agent/.env" ]; then
            cp "$PROJECT_ROOT/neuraops-agent/.env.example" "$PROJECT_ROOT/neuraops-agent/.env" 2>/dev/null || true
            print_info "Created neuraops-agent/.env - Please configure it"
        fi
        
        # UI .env
        if [ ! -f "$PROJECT_ROOT/neuraops-ui/.env" ]; then
            cp "$PROJECT_ROOT/neuraops-ui/.env.example" "$PROJECT_ROOT/neuraops-ui/.env" 2>/dev/null || true
            print_info "Created neuraops-ui/.env - Please configure it"
        fi
        
        # Docker .env
        if [ ! -f "$PROJECT_ROOT/docker/neuraops/.env" ]; then
            cp "$PROJECT_ROOT/docker/neuraops/.env.example" "$PROJECT_ROOT/docker/neuraops/.env" 2>/dev/null || true
            print_info "Created docker/neuraops/.env - Please configure it"
        fi
        
        print_success "Environment files created"
    fi
}

# Create necessary directories
create_directories() {
    print_step "Creating necessary directories..."
    
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/data"
    mkdir -p "$PROJECT_ROOT/dist"
    
    print_success "Directories created"
}

# Verify installation
verify_installation() {
    print_step "Verifying installation..."
    
    # Test Core import
    cd "$PROJECT_ROOT/neuraops-core"
    if command -v uv &> /dev/null; then
        if uv run python -c "from src.main import app" 2>/dev/null; then
            print_success "Core module imports successfully"
        else
            print_error "Core module import failed"
        fi
    fi
    
    # Test Agent import
    cd "$PROJECT_ROOT/neuraops-agent"
    if command -v uv &> /dev/null; then
        if uv run python -c "from src.main import app" 2>/dev/null; then
            print_success "Agent module imports successfully"
        else
            print_error "Agent module import failed"
        fi
    fi
    
    # Test UI build
    cd "$PROJECT_ROOT/neuraops-ui"
    if [ -d "node_modules" ]; then
        print_success "UI dependencies installed"
    else
        print_error "UI dependencies not found"
    fi
}

# Print next steps
print_next_steps() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Installation completed successfully!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo "1. Configure environment files:"
    echo "   - neuraops-core/.env"
    echo "   - neuraops-agent/.env"
    echo "   - neuraops-ui/.env"
    echo ""
    echo "2. Start Ollama (if installed):"
    echo "   ollama serve"
    echo ""
    echo "3. Run the development environment:"
    echo "   ./scripts/dev.sh"
    echo ""
    echo "4. Or build for production:"
    echo "   ./scripts/build.sh all production"
    echo ""
}

# Main installation process
main() {
    echo "Starting NeuraOps installation..."
    echo ""
    
    # Detect OS
    detect_os
    
    # Check prerequisites
    check_python
    check_nodejs
    
    # Install tools
    install_uv
    install_ollama
    
    # Setup environments
    setup_python_env
    setup_nodejs_env
    
    # Setup configuration
    setup_env_files
    create_directories
    
    # Verify
    verify_installation
    
    # Done
    print_next_steps
}

# Run main function
main "$@"