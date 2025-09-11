#!/bin/bash

# =========================================================================
# NeuraOps Clean Script
# Clean build artifacts, caches, and temporary files
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

# Clean options
CLEAN_LEVEL="${1:-standard}"  # standard, deep, all
DRY_RUN="${2:-false}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           NeuraOps Project Clean Script                ║${NC}"
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

# Function to remove directory/file
safe_remove() {
    local path="$1"
    local description="$2"
    
    if [ -e "$path" ]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            print_info "Would remove: $description ($path)"
        else
            rm -rf "$path"
            print_success "Removed: $description"
        fi
    fi
}

# Clean Python cache and build files
clean_python() {
    print_step "Cleaning Python cache and build files..."
    
    # Clean Core
    cd "$PROJECT_ROOT/neuraops-core"
    safe_remove "__pycache__" "Core Python cache"
    safe_remove ".pytest_cache" "Core pytest cache"
    safe_remove "*.egg-info" "Core egg-info"
    safe_remove "dist" "Core dist directory"
    safe_remove "build" "Core build directory"
    safe_remove ".coverage" "Core coverage file"
    safe_remove "htmlcov" "Core coverage HTML"
    safe_remove ".mypy_cache" "Core mypy cache"
    
    # Find and remove all __pycache__ directories
    if [[ "$DRY_RUN" == "false" ]]; then
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        find . -type f -name "*.pyo" -delete 2>/dev/null || true
    fi
    
    # Clean Agent
    cd "$PROJECT_ROOT/neuraops-agent"
    safe_remove "__pycache__" "Agent Python cache"
    safe_remove ".pytest_cache" "Agent pytest cache"
    safe_remove "*.egg-info" "Agent egg-info"
    safe_remove "dist" "Agent dist directory"
    safe_remove "build" "Agent build directory"
    safe_remove ".coverage" "Agent coverage file"
    safe_remove "htmlcov" "Agent coverage HTML"
    safe_remove ".mypy_cache" "Agent mypy cache"
    
    # Find and remove all __pycache__ directories
    if [[ "$DRY_RUN" == "false" ]]; then
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        find . -type f -name "*.pyo" -delete 2>/dev/null || true
    fi
    
    print_success "Python files cleaned"
}

# Clean Node.js files
clean_nodejs() {
    print_step "Cleaning Node.js build files..."
    
    cd "$PROJECT_ROOT/neuraops-ui"
    safe_remove ".next" "Next.js build directory"
    safe_remove "out" "Next.js export directory"
    safe_remove ".turbo" "Turbo cache"
    safe_remove "coverage" "Test coverage"
    
    print_success "Node.js files cleaned"
}

# Clean Docker volumes and images (deep clean)
clean_docker() {
    if [[ "$CLEAN_LEVEL" == "deep" ]] || [[ "$CLEAN_LEVEL" == "all" ]]; then
        print_step "Cleaning Docker resources..."
        
        if command -v docker &> /dev/null; then
            if [[ "$DRY_RUN" == "true" ]]; then
                print_info "Would remove Docker containers, volumes, and images"
            else
                # Stop and remove containers
                docker-compose -f "$PROJECT_ROOT/docker/neuraops/docker-compose.yml" down -v 2>/dev/null || true
                
                # Remove NeuraOps images
                docker images | grep neuraops | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
                
                # Prune dangling images
                docker image prune -f 2>/dev/null || true
                
                print_success "Docker resources cleaned"
            fi
        else
            print_info "Docker not installed, skipping Docker cleanup"
        fi
    fi
}

# Clean virtual environments (deep clean)
clean_venv() {
    if [[ "$CLEAN_LEVEL" == "deep" ]] || [[ "$CLEAN_LEVEL" == "all" ]]; then
        print_step "Cleaning virtual environments..."
        
        # Core venv
        safe_remove "$PROJECT_ROOT/neuraops-core/venv" "Core virtual environment"
        safe_remove "$PROJECT_ROOT/neuraops-core/.venv" "Core UV environment"
        
        # Agent venv
        safe_remove "$PROJECT_ROOT/neuraops-agent/venv" "Agent virtual environment"
        safe_remove "$PROJECT_ROOT/neuraops-agent/.venv" "Agent UV environment"
        
        print_success "Virtual environments cleaned"
    fi
}

# Clean node_modules (all clean)
clean_node_modules() {
    if [[ "$CLEAN_LEVEL" == "all" ]]; then
        print_step "Cleaning node_modules..."
        
        safe_remove "$PROJECT_ROOT/neuraops-ui/node_modules" "UI node_modules"
        safe_remove "$PROJECT_ROOT/neuraops-ui/pnpm-lock.yaml" "pnpm lock file"
        safe_remove "$PROJECT_ROOT/neuraops-ui/package-lock.json" "npm lock file"
        
        print_success "node_modules cleaned"
    fi
}

# Clean logs and temporary files
clean_logs() {
    print_step "Cleaning logs and temporary files..."
    
    # Project logs
    safe_remove "$PROJECT_ROOT/logs" "Log directory"
    safe_remove "$PROJECT_ROOT/*.log" "Root log files"
    
    # Temp files
    if [[ "$DRY_RUN" == "false" ]]; then
        find "$PROJECT_ROOT" -type f -name "*.tmp" -delete 2>/dev/null || true
        find "$PROJECT_ROOT" -type f -name "*.swp" -delete 2>/dev/null || true
        find "$PROJECT_ROOT" -type f -name ".DS_Store" -delete 2>/dev/null || true
    fi
    
    print_success "Logs and temp files cleaned"
}

# Clean distribution files
clean_dist() {
    print_step "Cleaning distribution files..."
    
    safe_remove "$PROJECT_ROOT/dist" "Distribution directory"
    
    print_success "Distribution files cleaned"
}

# Clean environment files (all clean)
clean_env() {
    if [[ "$CLEAN_LEVEL" == "all" ]]; then
        print_step "Cleaning environment files..."
        
        print_info "Preserving .env.example files"
        
        if [[ "$DRY_RUN" == "true" ]]; then
            print_info "Would remove .env files (keeping .env.example)"
        else
            # Remove .env files but keep .env.example
            find "$PROJECT_ROOT" -name ".env" -not -name ".env.example" -type f -delete 2>/dev/null || true
        fi
        
        print_success "Environment files cleaned"
    fi
}

# Calculate space saved
calculate_space() {
    if [[ "$DRY_RUN" == "false" ]]; then
        print_step "Calculating space saved..."
        
        # This is a simplified calculation
        # In a real scenario, you'd track before and after sizes
        print_info "Space reclaimed (estimate)"
    fi
}

# Summary
print_summary() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${GREEN}Dry run completed - no files were removed${NC}"
    else
        echo -e "${GREEN}Cleaning completed successfully!${NC}"
    fi
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    
    echo -e "${CYAN}Clean levels:${NC}"
    echo "  • standard - Cache, build files, logs"
    echo "  • deep     - Above + Docker, virtual environments"
    echo "  • all      - Everything including node_modules, .env files"
    echo ""
    
    if [[ "$DRY_RUN" == "false" ]]; then
        echo -e "${CYAN}To rebuild:${NC}"
        echo "  ./scripts/install.sh  # Reinstall dependencies"
        echo "  ./scripts/build.sh    # Build project"
    fi
}

# Main function
main() {
    echo "Clean Level: $CLEAN_LEVEL"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "Mode: Dry Run (no files will be removed)"
    else
        echo "Mode: Clean (files will be removed)"
    fi
    echo ""
    
    # Perform cleaning based on level
    case "$CLEAN_LEVEL" in
        standard)
            clean_python
            clean_nodejs
            clean_logs
            clean_dist
            ;;
        deep)
            clean_python
            clean_nodejs
            clean_docker
            clean_venv
            clean_logs
            clean_dist
            ;;
        all)
            clean_python
            clean_nodejs
            clean_docker
            clean_venv
            clean_node_modules
            clean_logs
            clean_dist
            clean_env
            ;;
        *)
            print_error "Invalid clean level: $CLEAN_LEVEL"
            echo "Usage: $0 [standard|deep|all] [dry-run]"
            exit 1
            ;;
    esac
    
    # Calculate and show summary
    calculate_space
    print_summary
}

# Parse arguments
if [[ "$2" == "dry-run" ]]; then
    DRY_RUN=true
fi

# Run main function
main