# NeuraOps Scripts

Collection of scripts to automate common tasks for the NeuraOps project.

## 📜 Available Scripts

### 🔧 **install.sh** - Complete Installation
Complete installation of NeuraOps and its dependencies.

```bash
./scripts/install.sh
```

**Features:**
- Checks prerequisites (Python 3.11+, Node.js 18+)
- Installs UV package manager
- Sets up Python environments for Core and Agent
- Installs Node.js dependencies for UI
- Creates .env files from templates
- Verifies installation

**Environment variables:**
- `INSTALL_UV=true/false` - Install UV (default: true)
- `INSTALL_OLLAMA=true/false` - Install Ollama (default: false)
- `SETUP_ENV=true/false` - Create .env files (default: true)

---

### 🏗️ **build.sh** - Project Build
Build all NeuraOps components for production or development.

```bash
# Complete build for production
./scripts/build.sh all production

# Build specific component
./scripts/build.sh core
./scripts/build.sh agent
./scripts/build.sh ui
./scripts/build.sh docker

# Build for development
./scripts/build.sh all development
```

**Options:**
- `all` - Build all components (default)
- `core` - Build NeuraOps Core only
- `agent` - Build NeuraOps Agent only
- `ui` - Build NeuraOps UI only
- `docker` - Build Docker images only

**Environments:**
- `production` - Optimized build for production (default)
- `development` - Build for development

---

### 🚀 **dev.sh** - Development Environment
Launch development environment with automatic reloading.

```bash
# Standard startup (Core API + UI)
./scripts/dev.sh

# Advanced options
./scripts/dev.sh --with-agent     # Include agent
./scripts/dev.sh --with-ollama    # Auto-start Ollama
./scripts/dev.sh --no-core        # Without Core API
./scripts/dev.sh --no-ui          # Without UI interface
```

**Services started:**
- **Core API**: http://localhost:8000 (with docs at /docs)
- **Web UI**: http://localhost:3000
- **Agent**: Background service (if --with-agent)

**Controls:**
- `Ctrl+C` - Stop all services
- Automatic service monitoring

---

### 🧹 **clean.sh** - Project Cleanup
Cleans build files, cache, and temporary files.

```bash
# Standard cleanup
./scripts/clean.sh

# Deep cleanup
./scripts/clean.sh deep

# Complete cleanup
./scripts/clean.sh all

# Simulation (dry-run)
./scripts/clean.sh standard dry-run
```

**Cleanup levels:**

#### **Standard**
- Python cache (`__pycache__`, `.pytest_cache`)
- Build files (`dist/`, `build/`, `.next/`)
- Logs and temporary files

#### **Deep**
- Everything from standard level
- Virtual environments (`venv/`, `.venv/`)
- Docker images and containers

#### **All**
- Everything from deep level
- `node_modules/`
- `.env` files (keeps `.env.example`)

---

## 🎯 Typical Workflows

### Initial Installation
```bash
# 1. Complete installation
./scripts/install.sh

# 2. Manual .env configuration
nano neuraops-core/.env
nano neuraops-agent/.env
nano neuraops-ui/.env

# 3. Start Ollama (if installed)
ollama serve

# 4. Development test
./scripts/dev.sh
```

### Daily Development
```bash
# Start environment
./scripts/dev.sh

# In another terminal: tests/modifications
cd neuraops-core
uv run python -m src.main health --verbose

# Periodic cleanup
./scripts/clean.sh standard
```

### Production Build
```bash
# Complete cleanup
./scripts/clean.sh deep

# Production build
./scripts/build.sh all production

# Test the build
cd dist/ && ls -la
```

### Complete Reset
```bash
# Total cleanup
./scripts/clean.sh all

# Reinstallation
./scripts/install.sh

# Rebuild
./scripts/build.sh all
```

---

## ⚙️ Configuration

### Global Environment Variables

```bash
# Installation
export INSTALL_UV=true
export INSTALL_OLLAMA=false
export SETUP_ENV=true

# Development
export NEXT_PUBLIC_API_URL=http://localhost:8000
export OLLAMA_BASE_URL=http://localhost:11434
```

### System Prerequisites
- **Python** 3.11+ with pip
- **Node.js** 18+ with npm
- **UV** (installed automatically)
- **Ollama** (optional, for AI)
- **Docker** (optional, for containerization)

---

## 🔍 Troubleshooting

### Common Errors

#### "Python 3.11+ required"
```bash
# Check version
python3 --version

# On macOS with Homebrew
brew install python@3.11
```

#### "Node.js 18+ required"
```bash
# Check version
node --version

# Installation with nvm
nvm install 18
nvm use 18
```

#### "UV not found"
```bash
# Manual installation
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

#### "Ollama connection failed"
```bash
# Check Ollama
ollama serve

# In another terminal
curl http://localhost:11434/api/tags
```

### Debugging Logs
```bash
# Core API logs
cd neuraops-core
uv run python -m src.main health --verbose

# Agent logs
cd neuraops-agent
uv run python -m src.main status

# UI logs (in browser)
# Developer console: F12
```

---

## 📁 Scripts Structure

```
scripts/
├── README.md           # This file
├── install.sh          # Complete installation
├── build.sh            # Project build
├── dev.sh              # Development environment
└── clean.sh            # Project cleanup
```

---

To add new scripts:

1. Create the script in `scripts/`
2. Make it executable: `chmod +x scripts/new-script.sh`
3. Follow the format of existing scripts
4. Document in this README
5. Test on different OS (macOS, Linux)

**Script template:**
```bash
#!/bin/bash
set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Functions
print_step() { echo -e "${YELLOW}▸ $1${NC}"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }

# Main logic
main() {
    print_step "Starting..."
    # ... script logic ...
    print_success "Done!"
}

main "$@"
```
