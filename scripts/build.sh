#!/bin/bash

# =========================================================================
# NeuraOps Build Script
# Build all components of the NeuraOps platform
# =========================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Build configuration
BUILD_TYPE="${1:-all}"  # all, core, agent, ui, docker
ENVIRONMENT="${2:-production}"  # production, development

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           NeuraOps Platform Build Script               ║${NC}"
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

# Function to check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3.11+ is required but not installed"
        exit 1
    fi
    
    # Check Node.js for UI
    if [[ "$BUILD_TYPE" == "all" || "$BUILD_TYPE" == "ui" ]]; then
        if ! command -v node &> /dev/null; then
            print_error "Node.js 18+ is required for UI but not installed"
            exit 1
        fi
    fi
    
    # Check Docker for docker build
    if [[ "$BUILD_TYPE" == "docker" ]]; then
        if ! command -v docker &> /dev/null; then
            print_error "Docker is required but not installed"
            exit 1
        fi
    fi
    
    print_success "Prerequisites check passed"
}

# Function to build NeuraOps Core
build_core() {
    print_step "Building NeuraOps Core..."
    cd "$PROJECT_ROOT/neuraops-core"
    
    # Check if UV is installed
    if command -v uv &> /dev/null; then
        print_step "Installing dependencies with UV..."
        uv sync
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            print_step "Building production package..."
            uv build
        fi
    else
        print_step "Installing dependencies with pip..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -e .
    fi
    
    print_success "NeuraOps Core built successfully"
}

# Function to build NeuraOps Agent
build_agent() {
    print_step "Building NeuraOps Agent..."
    cd "$PROJECT_ROOT/neuraops-agent"
    
    # Check if UV is installed
    if command -v uv &> /dev/null; then
        print_step "Installing dependencies with UV..."
        uv sync
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            print_step "Building production package..."
            uv build
        fi
    else
        print_step "Installing dependencies with pip..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -e .
    fi
    
    print_success "NeuraOps Agent built successfully"
}

# Function to build NeuraOps UI
build_ui() {
    print_step "Building NeuraOps UI..."
    cd "$PROJECT_ROOT/neuraops-ui"
    
    # Install dependencies
    print_step "Installing Node.js dependencies..."
    if command -v pnpm &> /dev/null; then
        pnpm install
    else
        npm install
    fi
    
    # Build for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        print_step "Building production UI..."
        npm run build
        
        # Check if build was successful
        if [ -d ".next" ]; then
            print_success "Production UI build complete"
        else
            print_error "UI build failed - .next directory not created"
            exit 1
        fi
    else
        print_success "Development UI dependencies installed"
    fi
    
    print_success "NeuraOps UI built successfully"
}

# Function to build Docker images
build_docker() {
    print_step "Building Docker images..."
    
    # Build Core image
    print_step "Building neuraops-core image..."
    docker build -t neuraops-core:latest \
        -f "$PROJECT_ROOT/docker/images/neuraops-core/Dockerfile" \
        "$PROJECT_ROOT"
    
    # Build Agent image
    print_step "Building neuraops-agent image..."
    docker build -t neuraops-agent:latest \
        -f "$PROJECT_ROOT/docker/images/neuraops-agent/Dockerfile" \
        "$PROJECT_ROOT"
    
    # Build UI image
    print_step "Building neuraops-ui image..."
    docker build -t neuraops-ui:latest \
        -f "$PROJECT_ROOT/docker/images/neuraops-ui/Dockerfile" \
        "$PROJECT_ROOT"
    
    print_success "Docker images built successfully"
}

# Function to create distribution packages
create_dist() {
    print_step "Creating distribution packages..."
    
    # Create dist directory
    DIST_DIR="$PROJECT_ROOT/dist"
    rm -rf "$DIST_DIR"
    mkdir -p "$DIST_DIR"
    
    # Package Core
    if [ -d "$PROJECT_ROOT/neuraops-core/dist" ]; then
        cp -r "$PROJECT_ROOT/neuraops-core/dist/"* "$DIST_DIR/"
        print_success "Core package copied to dist"
    fi
    
    # Package Agent
    if [ -d "$PROJECT_ROOT/neuraops-agent/dist" ]; then
        cp -r "$PROJECT_ROOT/neuraops-agent/dist/"* "$DIST_DIR/"
        print_success "Agent package copied to dist"
    fi
    
    # Package UI
    if [ -d "$PROJECT_ROOT/neuraops-ui/.next" ]; then
        tar -czf "$DIST_DIR/neuraops-ui.tar.gz" -C "$PROJECT_ROOT/neuraops-ui" .next public package.json
        print_success "UI package created"
    fi
    
    print_success "Distribution packages created in $DIST_DIR"
}

# Main build process
main() {
    echo "Build Type: $BUILD_TYPE"
    echo "Environment: $ENVIRONMENT"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Execute build based on type
    case "$BUILD_TYPE" in
        core)
            build_core
            ;;
        agent)
            build_agent
            ;;
        ui)
            build_ui
            ;;
        docker)
            build_docker
            ;;
        all)
            build_core
            build_agent
            build_ui
            if [[ "$ENVIRONMENT" == "production" ]]; then
                create_dist
            fi
            ;;
        *)
            print_error "Invalid build type: $BUILD_TYPE"
            echo "Usage: $0 [all|core|agent|ui|docker] [production|development]"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
}

# Run main function
main