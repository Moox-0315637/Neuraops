# NeuraOps

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Next.js](https://img.shields.io/badge/next.js-15.x-black.svg)
![Status](https://img.shields.io/badge/status-alpha-orange.svg)

**AI-Powered DevOps Assistant for Air-gapped Environments**

NeuraOps is a comprehensive DevOps platform that leverages OpenAI's gpt-oss-20b model via Ollama to provide intelligent infrastructure management, incident response, and operational automation for air-gapped and secure environments.

## 🏗️ Architecture

NeuraOps follows a distributed three-component architecture:

```
                                                                        
   🏢 NeuraOps Core         🤖 NeuraOps Agent        🖥️ NeuraOps UI     
                                                                        
 ├── FastAPI Server       ├── System Monitoring       ├── Next.js 15 App    
 ├── AI Engine            ├── Command Execution       ├── Real-time UI      
 ├── Command Center       ├── Health Reporting        ├── Agent Management  
 ├── WebSocket Hub        ├── Secure Connection       ├── Workflow Designer 
                                                                        
```

### Components

- **NeuraOps Core**: Central control plane with AI engine, API server, and agent orchestration
- **NeuraOps Agent**: Lightweight clients for distributed system monitoring and command execution
- **NeuraOps UI**: Modern web interface built with Next.js 15 and TypeScript

## ✨ Features

### 🧠 AI-Powered Operations
- **Intelligent Log Analysis**: Automated log parsing with severity detection and recommendations
- **Incident Response**: AI-driven incident detection and automated response playbooks
- **Infrastructure Generation**: Generate Terraform, Kubernetes, and Docker configurations
- **Predictive Analytics**: Forecasting and anomaly detection for system health

### ⚡ DevOps Automation
- **Multi-Cloud Support**: AWS, Azure, GCP, OCI, and Digital Ocean
- **Container Orchestration**: Docker and Kubernetes management
- **Deployment Strategies**: Rolling, blue-green, canary, and instant deployments
- **Infrastructure as Code**: Terraform and configuration template generation

### 🔒 Security & Safety
- **Air-gapped Compatible**: Designed for secure, isolated environments
- **Command Safety Validation**: Multi-level safety checks before execution
- **JWT Authentication**: Secure agent-to-core communication
- **Audit Trail**: Complete logging of all operations and decisions

### 📊 Monitoring & Observability
- **Real-time Metrics**: System health and performance monitoring
- **Distributed Agents**: Monitor multiple systems from a central dashboard
- **Alert Management**: Intelligent alerting with context-aware notifications
- **Health Dashboards**: Visual system status and operational insights

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** for Core and Agent components
- **Node.js 18+** for UI component
- **UV Package Manager** for Python dependency management
- **Ollama** with gpt-oss-20b model for AI capabilities
- **Docker** (optional, for containerized deployment)

### Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/neuraops/neuraops.git
cd neuraops
```

#### 2. Setup Core Platform
```bash
cd neuraops-core

# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure Ollama connection
export OLLAMA_BASE_URL="https://your-ollama-instance"
export OLLAMA_MODEL="gpt-oss:20b"

# Test installation
uv run python -m src.main health --verbose
```

#### 3. Setup Agent Client (Optional)
```bash
cd ../neuraops-agent

# Install agent dependencies
uv sync

# Register with core platform
uv run python -m src.main register --name my-agent

# Start agent daemon
uv run python -m src.main start --daemon
```

#### 4. Setup Web UI
```bash
cd ../neuraops-ui

# Install Node.js dependencies
npm install

# Start development server
npm run dev
```

Access the UI at `http://localhost:3000`

### Docker Deployment

For production deployment using Docker Compose:

```bash
cd docker/neuraops

# Configure environment variables
cp .env.example .env
# Edit .env with your Ollama and database settings

# Start all services
docker-compose up -d
```

Services will be available at:
- **Core API**: `http://localhost:8000`
- **Web UI**: `http://localhost:3000`
- **Redis**: `localhost:6379`
- **PostgreSQL**: `localhost:5432`

## 💻 Usage Examples

### Command Line Interface

```bash
# Health check with AI validation
uv run python -m src.main health --verbose

# Intelligent log analysis
uv run python -m src.main logs /var/log/syslog --ai

# Generate infrastructure configuration
uv run python -m src.main infra "3-tier web application on AWS"

# Incident response simulation
uv run python -m src.main incidents --scenario database-outage

# Start workflow execution
uv run python -m src.main workflow run deployment-pipeline

# Launch interactive demo
uv run python -m src.main demo
```

### API Integration

```python
import httpx

# Connect to NeuraOps API
client = httpx.Client(base_url="http://localhost:8000")

# Analyze logs with AI
response = client.post("/api/v1/analyze/logs", json={
    "content": "ERROR: Database connection timeout",
    "source": "/var/log/app.log"
})

# Get agent status
agents = client.get("/api/v1/agents").json()
print(f"Active agents: {len(agents['agents'])}")
```

### Agent Operations

```bash
# Register new agent
neuraops-agent register --name production-server-01

# Monitor system health
neuraops-agent monitor --interval 30

# Execute secure command
neuraops-agent execute "systemctl status nginx" --safety-check

# Report system metrics
neuraops-agent collect --metrics cpu,memory,disk
```

## 🔧 Development

### Development Setup

```bash
# Core platform development
cd neuraops-core
uv run pytest tests/ --cov=src

# Code quality checks
uv run black src/ tests/
uv run mypy src/
uv run bandit -r src/

# Agent development
cd ../neuraops-agent
uv run pytest tests/ --cov=src

# UI development
cd ../neuraops-ui
npm run lint
npm run type-check
npm test
```

### Testing

Each component includes comprehensive test suites:

- **Unit Tests**: Core logic and AI integration
- **Integration Tests**: API endpoints and database operations
- **End-to-End Tests**: Full workflow validation
- **Safety Tests**: Command validation and security checks

```bash
# Run all tests
cd neuraops-core && uv run pytest
cd neuraops-agent && uv run pytest
cd neuraops-ui && npm test
```

## 📁 Project Structure

```
NeuraOps/
├── 🏢 neuraops-core/          # Central Control Plane
│   ├── src/
│   │   ├── api/               # FastAPI server and routes
│   │   ├── cli/               # Command-line interface
│   │   ├── core/              # AI engine and core logic
│   │   ├── modules/           # Specialized DevOps modules
│   │   └── main.py            # CLI entry point
│   ├── tests/                 # Core platform tests
│   └── pyproject.toml         # Python dependencies
├── 🤖 neuraops-agent/         # Distributed Agent Client
│   ├── src/
│   │   ├── agent.py           # Core agent orchestrator
│   │   ├── collector.py       # System monitoring
│   │   ├── executor.py        # Command execution
│   │   └── main.py            # Agent CLI entry point
│   └── tests/                 # Agent tests
├── 🖥️ neuraops-ui/            # Modern Next.js UI
│   ├── src/
│   │   ├── app/               # Next.js app router
│   │   ├── components/        # React components
│   │   ├── services/          # API integration
│   │   └── stores/            # Zustand state management
│   └── package.json           # Node.js dependencies
├── 🐳 docker/                 # Containerization
│   └── neuraops/              # Docker Compose setup
├── 📚 docs/                   # Documentation
├── 🛠️ scripts/                # Utility scripts
└── 📋 CLAUDE.md               # Development guidelines
```

## 🔗 Integrations

### AI & Machine Learning
- **Ollama**: OpenAI gpt-oss-20b model integration
- **Structured Output**: Pydantic-validated AI responses
- **Caching**: Redis-based AI response caching

### Infrastructure
- **Terraform**: Multi-cloud infrastructure generation
- **Kubernetes**: Container orchestration
- **Docker**: Containerization and deployment

### Monitoring & Observability
- **Redis**: Caching and session storage
- **PostgreSQL**: Persistent data storage
- **WebSocket**: Real-time communication
- **Structured Logging**: JSON-based log aggregation

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**: Follow our coding standards
4. **Add tests**: Ensure comprehensive test coverage
5. **Run quality checks**: `./scripts/quality-check.sh`
6. **Submit a pull request**

### Code Standards

- **Python**: Black formatting, MyPy type checking, 100-char line limit
- **TypeScript**: ESLint rules, Prettier formatting
- **Documentation**: Keep docs synchronized with code changes
- **Testing**: Maintain >80% test coverage

## 🙏 Acknowledgments

- **OpenAI** for the gpt-oss-20b model
- **Ollama** for local AI model hosting
- **FastAPI** for the robust API framework
- **Next.js** for the modern UI framework
- **Typer** for the intuitive CLI interface

**NeuraOps** - Empowering DevOps teams with AI-driven automation and intelligent operations management.
