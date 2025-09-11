#!/bin/bash

# =========================================================================
# NeuraOps Development Environment Script
# Start all services in development mode
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

# Development options
START_CORE="${1:-true}"
START_AGENT="${2:-false}"
START_UI="${3:-true}"
START_OLLAMA="${4:-false}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      NeuraOps Development Environment Manager          ║${NC}"
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

# Trap to cleanup on exit
cleanup() {
    echo ""
    print_info "Shutting down development environment..."
    
    # Kill all background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    
    print_success "Development environment stopped"
}
trap cleanup EXIT INT TERM

# Check if Ollama is running
check_ollama() {
    print_step "Checking Ollama status..."
    
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        print_success "Ollama is running"
        return 0
    else
        print_error "Ollama is not running"
        
        if [[ "$START_OLLAMA" == "true" ]]; then
            print_step "Starting Ollama..."
            ollama serve &
            OLLAMA_PID=$!
            sleep 5
            
            if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
                print_success "Ollama started successfully"
            else
                print_error "Failed to start Ollama"
                exit 1
            fi
        else
            print_info "Run 'ollama serve' in another terminal or use './dev.sh true false true true' to auto-start"
            return 1
        fi
    fi
}

# Start NeuraOps Core API
start_core() {
    if [[ "$START_CORE" == "true" ]]; then
        print_step "Starting NeuraOps Core API..."
        
        cd "$PROJECT_ROOT/neuraops-core"
        
        # Check for .env file
        if [ ! -f ".env" ]; then
            print_error "neuraops-core/.env not found. Run ./scripts/install.sh first"
            exit 1
        fi
        
        # Start API server
        if command -v uv &> /dev/null; then
            print_info "Starting Core API on http://localhost:8000"
            uv run uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000 &
            CORE_PID=$!
        else
            source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
            print_info "Starting Core API on http://localhost:8000"
            uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000 &
            CORE_PID=$!
        fi
        
        sleep 3
        
        # Check if API is running
        if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
            print_success "Core API started successfully"
            print_info "API Docs: http://localhost:8000/docs"
        else
            print_error "Core API failed to start"
        fi
    fi
}

# Start NeuraOps Agent
start_agent() {
    if [[ "$START_AGENT" == "true" ]]; then
        print_step "Starting NeuraOps Agent..."
        
        cd "$PROJECT_ROOT/neuraops-agent"
        
        # Check for .env file
        if [ ! -f ".env" ]; then
            print_error "neuraops-agent/.env not found. Run ./scripts/install.sh first"
            exit 1
        fi
        
        # Start agent
        if command -v uv &> /dev/null; then
            print_info "Starting Agent..."
            uv run python -m src.main start &
            AGENT_PID=$!
        else
            source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
            print_info "Starting Agent..."
            python -m src.main start &
            AGENT_PID=$!
        fi
        
        sleep 2
        print_success "Agent started"
    fi
}

# Start NeuraOps UI
start_ui() {
    if [[ "$START_UI" == "true" ]]; then
        print_step "Starting NeuraOps UI..."
        
        cd "$PROJECT_ROOT/neuraops-ui"
        
        # Check for node_modules
        if [ ! -d "node_modules" ]; then
            print_error "UI dependencies not installed. Run ./scripts/install.sh first"
            exit 1
        fi
        
        # Set API URL if not set
        export NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
        
        print_info "Starting UI on http://localhost:3000"
        
        # Start Next.js dev server
        if command -v pnpm &> /dev/null; then
            pnpm dev &
            UI_PID=$!
        else
            npm run dev &
            UI_PID=$!
        fi
        
        sleep 5
        print_success "UI started on http://localhost:3000"
    fi
}

# Show running services
show_status() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Development Environment Running${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Services:${NC}"
    
    if [[ "$START_CORE" == "true" ]]; then
        echo "  • Core API:    http://localhost:8000"
        echo "  • API Docs:    http://localhost:8000/docs"
    fi
    
    if [[ "$START_UI" == "true" ]]; then
        echo "  • Web UI:      http://localhost:3000"
    fi
    
    if [[ "$START_AGENT" == "true" ]]; then
        echo "  • Agent:       Running"
    fi
    
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "  • Ollama:      http://localhost:11434"
    fi
    
    echo ""
    echo -e "${CYAN}Commands:${NC}"
    echo "  • View logs:   Check terminal output"
    echo "  • Stop:        Press Ctrl+C"
    echo ""
    echo -e "${CYAN}Quick Test:${NC}"
    echo "  curl http://localhost:8000/api/health"
    echo ""
}

# Monitor services
monitor_services() {
    print_info "Monitoring services... (Press Ctrl+C to stop)"
    
    while true; do
        # Check if services are still running
        if [[ "$START_CORE" == "true" ]] && ! kill -0 $CORE_PID 2>/dev/null; then
            print_error "Core API stopped unexpectedly"
            exit 1
        fi
        
        if [[ "$START_UI" == "true" ]] && ! kill -0 $UI_PID 2>/dev/null; then
            print_error "UI stopped unexpectedly"
            exit 1
        fi
        
        if [[ "$START_AGENT" == "true" ]] && ! kill -0 $AGENT_PID 2>/dev/null; then
            print_error "Agent stopped unexpectedly"
            exit 1
        fi
        
        sleep 5
    done
}

# Main function
main() {
    echo "Starting development environment..."
    echo ""
    
    # Check Ollama
    check_ollama
    
    # Start services
    start_core
    start_agent
    start_ui
    
    # Show status
    show_status
    
    # Monitor services
    monitor_services
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-core)
            START_CORE=false
            shift
            ;;
        --no-ui)
            START_UI=false
            shift
            ;;
        --with-agent)
            START_AGENT=true
            shift
            ;;
        --with-ollama)
            START_OLLAMA=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --no-core      Don't start Core API"
            echo "  --no-ui        Don't start Web UI"
            echo "  --with-agent   Start Agent service"
            echo "  --with-ollama  Auto-start Ollama"
            echo "  --help         Show this help"
            echo ""
            echo "Default: Starts Core API and UI"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage"
            exit 1
            ;;
    esac
done

# Run main function
main